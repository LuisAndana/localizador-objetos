"""Acceso a datos. Unico lugar del proyecto que conoce DynamoDB."""

import logging
import uuid

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeSerializer
from botocore.config import Config as ConfigBoto
from botocore.exceptions import ClientError

from . import config, metricas, plano, validacion
from .errores import ErrorConflicto, ErrorNoEncontrado, ErrorValidacion
from .modelos import ahora_iso, ahora_iso_preciso

logger = logging.getLogger(__name__)

_CONFIG_BOTO = ConfigBoto(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=2,
    read_timeout=5,
)

_recurso = None
_serializador = TypeSerializer()


def _a_dynamo(datos: dict) -> dict:
    """Traduce al formato de bajo nivel que exige transact_write_items."""
    return {clave: _serializador.serialize(valor) for clave, valor in datos.items()}


def _recurso_dynamodb():
    """Cacheado a nivel de modulo: se reutiliza entre invocaciones warm."""
    global _recurso
    if _recurso is None:
        _recurso = boto3.resource(
            "dynamodb", endpoint_url=config.endpoint_dynamodb(), config=_CONFIG_BOTO
        )
    return _recurso


# Copia normalizada del nombre (minusculas, sin acentos) que solo existe para
# buscar: DynamoDB no compara sin distinguir mayusculas ni acentos.
CAMPO_BUSQUEDA = "nombre_busqueda"


def _publico(item: dict) -> dict:
    """Lo que sale por la API: sin los campos internos de busqueda."""
    return {k: v for k, v in item.items() if k != CAMPO_BUSQUEDA}


def _ejecutar(operacion, parametros: dict) -> dict:
    try:
        return operacion(**parametros)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ValidationException":
            # Tipicamente un cursor que no corresponde a esta consulta.
            raise ErrorValidacion(
                "Los parametros de paginacion no son validos para esta consulta."
            ) from exc
        raise


class RepositorioObjetos:
    def __init__(self, nombre_tabla: str | None = None, indice: str | None = None):
        self._nombre_tabla = nombre_tabla or config.tabla_objetos()
        self._indice = indice or config.indice_categoria()
        self._tabla = _recurso_dynamodb().Table(self._nombre_tabla)

    def obtener(self, object_id: str) -> dict:
        respuesta = self._tabla.get_item(Key={"object_id": object_id})
        item = respuesta.get("Item")
        if not item:
            raise ErrorNoEncontrado(f"No existe ningun objeto con id '{object_id}'.")
        return _publico(item)

    def crear(self, datos: dict) -> dict:
        objeto_id = datos.get("object_id") or str(uuid.uuid4())
        item = {
            **{k: v for k, v in datos.items() if k != "object_id"},
            "object_id": objeto_id,
            CAMPO_BUSQUEDA: validacion.normalizar_busqueda(datos["nombre"]),
            "ultima_actualizacion": ahora_iso(),
        }
        try:
            self._tabla.put_item(
                Item=item, ConditionExpression="attribute_not_exists(object_id)"
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorConflicto(
                    f"Ya existe un objeto con id '{objeto_id}'."
                ) from exc
            raise
        return _publico(item)

    def actualizar(self, object_id: str, cambios: dict) -> dict:
        """Actualizacion parcial. Falla con 404 si el objeto no existe."""
        cambios = {**cambios, "ultima_actualizacion": ahora_iso()}
        if "nombre" in cambios:
            cambios[CAMPO_BUSQUEDA] = validacion.normalizar_busqueda(cambios["nombre"])

        asignaciones = []
        nombres: dict[str, str] = {}
        valores: dict[str, object] = {}
        for indice, (campo, valor) in enumerate(cambios.items()):
            alias_nombre = f"#c{indice}"
            alias_valor = f":v{indice}"
            asignaciones.append(f"{alias_nombre} = {alias_valor}")
            nombres[alias_nombre] = campo
            valores[alias_valor] = valor

        try:
            respuesta = self._tabla.update_item(
                Key={"object_id": object_id},
                UpdateExpression="SET " + ", ".join(asignaciones),
                ExpressionAttributeNames=nombres,
                ExpressionAttributeValues=valores,
                ConditionExpression="attribute_exists(object_id)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorNoEncontrado(
                    f"No existe ningun objeto con id '{object_id}'."
                ) from exc
            raise
        return _publico(respuesta["Attributes"])

    def eliminar(self, object_id: str) -> dict:
        """Solo borra si no quedan existencias: borrar material que sigue en el
        anaquel haria desaparecer inventario real del sistema."""
        try:
            respuesta = self._tabla.delete_item(
                Key={"object_id": object_id},
                ConditionExpression=(
                    "attribute_exists(object_id) "
                    "AND (attribute_not_exists(cantidad) OR cantidad = :cero)"
                ),
                ExpressionAttributeValues={":cero": 0},
                ReturnValues="ALL_OLD",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            actual = self._tabla.get_item(Key={"object_id": object_id}).get("Item")
            if actual is None:
                raise ErrorNoEncontrado(
                    f"No existe ningun objeto con id '{object_id}'."
                ) from exc
            quedan = int(actual.get("cantidad", 0))
            raise ErrorConflicto(
                f"Al objeto le quedan {quedan} piezas. Registra su salida antes de eliminarlo.",
                {"cantidad": quedan},
            ) from exc
        return _publico(respuesta["Attributes"])

    # --- Busqueda por nombre ------------------------------------------------
    # DynamoDB no tiene "contiene" sobre una clave: se recorre la tabla (o el
    # GSI, si hay categoria) filtrando por la copia normalizada del nombre. El
    # filtro se aplica despues de leer, asi que se siguen leyendo paginas hasta
    # juntar `limite` coincidencias o llegar al tope. Alcanza para cientos o
    # pocos miles de objetos; con decenas de miles hara falta un indice de texto.
    TAMANO_PAGINA_BUSQUEDA = 200
    MAXIMO_PAGINAS_BUSQUEDA = 10

    def buscar(
        self, termino: str, categoria: str | None, limite: int, cursor: dict | None = None
    ) -> tuple[list[dict], dict | None]:
        filtro = Attr(CAMPO_BUSQUEDA).contains(termino) | Attr("object_id").contains(termino)
        parametros: dict = {"FilterExpression": filtro, "Limit": self.TAMANO_PAGINA_BUSQUEDA}
        operacion = self._tabla.scan
        if categoria:
            operacion = self._tabla.query
            parametros["IndexName"] = self._indice
            parametros["KeyConditionExpression"] = Key("categoria").eq(categoria)
        if cursor:
            parametros["ExclusiveStartKey"] = cursor

        items: list[dict] = []
        ultima = None
        for _ in range(self.MAXIMO_PAGINAS_BUSQUEDA):
            respuesta = _ejecutar(operacion, parametros)
            items += respuesta.get("Items", [])
            ultima = respuesta.get("LastEvaluatedKey")
            if not ultima or len(items) >= limite:
                break
            parametros = {**parametros, "ExclusiveStartKey": ultima}
        # No se recorta a `limite`: el cursor apunta despues de la ultima pagina
        # leida, y recortar perderia coincidencias.
        return [_publico(i) for i in items], ultima

    def hay_en_categoria(self, categoria: str) -> bool:
        respuesta = _ejecutar(
            self._tabla.query,
            {
                "IndexName": self._indice,
                "KeyConditionExpression": Key("categoria").eq(categoria),
                "ProjectionExpression": "object_id",
                "Limit": 1,
            },
        )
        return bool(respuesta.get("Items"))

    def listar_por_categoria(
        self, categoria: str, limite: int, cursor: dict | None = None
    ) -> tuple[list[dict], dict | None]:
        parametros = {
            "IndexName": self._indice,
            "KeyConditionExpression": Key("categoria").eq(categoria),
            "Limit": limite,
        }
        if cursor:
            parametros["ExclusiveStartKey"] = cursor
        respuesta = _ejecutar(self._tabla.query, parametros)
        return [_publico(i) for i in respuesta.get("Items", [])], respuesta.get("LastEvaluatedKey")

    def listar_todos(
        self, limite: int, cursor: dict | None = None
    ) -> tuple[list[dict], dict | None]:
        """Scan completo: aceptable solo para catalogos pequenos o admin.

        El camino normal de la app cliente es `listar_por_categoria`, que va
        contra el GSI y no recorre la tabla entera.
        """
        parametros: dict = {"Limit": limite}
        if cursor:
            parametros["ExclusiveStartKey"] = cursor
        respuesta = _ejecutar(self._tabla.scan, parametros)
        return [_publico(i) for i in respuesta.get("Items", [])], respuesta.get("LastEvaluatedKey")

    # --- Plano del almacen -------------------------------------------------
    # El mapa se dibuja completo, asi que aqui no hay cursor: se recorren todas
    # las paginas del scan, con un tope para que una tabla grande no agote el
    # tiempo de la funcion. Se proyectan solo los campos que el mapa usa.
    PROYECCION_PLANO = (
        "object_id, nombre, categoria, almacen_id, pasillo, anaquel, nivel, columna, "
        "posicion_led, color_indicador"
    )
    MAXIMO_PAGINAS_PLANO = 20

    def _recorrer_scan(self, parametros: dict) -> list[dict]:
        items: list[dict] = []
        for _ in range(self.MAXIMO_PAGINAS_PLANO):
            respuesta = _ejecutar(self._tabla.scan, parametros)
            items += respuesta.get("Items", [])
            cursor = respuesta.get("LastEvaluatedKey")
            if not cursor:
                return items
            parametros = {**parametros, "ExclusiveStartKey": cursor}
        logger.warning(
            "Plano truncado: la tabla supera %s paginas de scan.", self.MAXIMO_PAGINAS_PLANO
        )
        return items

    def listar_por_almacen(self, almacen_id: str) -> list[dict]:
        return self._recorrer_scan(
            {
                "FilterExpression": Attr("almacen_id").eq(almacen_id),
                "ProjectionExpression": self.PROYECCION_PLANO,
            }
        )

    def resumen_almacenes(self) -> list[dict]:
        return plano.resumir_almacenes(
            self._recorrer_scan({"ProjectionExpression": "almacen_id, pasillo"})
        )


class RepositorioMovimientos:
    """Entradas y salidas en DynamoDB.

    El ajuste de la cantidad (tabla Objetos) y el historial (tabla Movimientos)
    se escriben con TransactWriteItems: o quedan los dos, o no queda ninguno.
    Sin eso, un fallo a medias dejaria existencias descontadas sin registro que
    lo explique, que es justo lo que audita el inventario.
    """

    def __init__(self, tabla_movimientos: str | None = None, tabla_objetos: str | None = None):
        self._nombre_movimientos = tabla_movimientos or config.tabla_movimientos()
        self._nombre_objetos = tabla_objetos or config.tabla_objetos()
        self._recurso = _recurso_dynamodb()
        self._tabla = self._recurso.Table(self._nombre_movimientos)

    def _objeto(self, object_id: str) -> dict | None:
        tabla = self._recurso.Table(self._nombre_objetos)
        return tabla.get_item(Key={"object_id": object_id}).get("Item")

    def registrar(self, movimiento: dict, delta: int) -> dict:
        object_id = movimiento["object_id"]
        # ADD suma sobre el valor actual en el servidor: dos salidas simultaneas
        # no se pisan como lo harian un GET y un PUT.
        condicion = "attribute_exists(object_id)"
        valores: dict = {":d": delta, ":ts": ahora_iso()}
        if delta < 0:
            condicion += " AND cantidad >= :minimo"
            valores[":minimo"] = -delta

        try:
            self._recurso.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self._nombre_objetos,
                            "Key": _a_dynamo({"object_id": object_id}),
                            "UpdateExpression": "SET ultima_actualizacion = :ts ADD cantidad :d",
                            "ConditionExpression": condicion,
                            "ExpressionAttributeValues": _a_dynamo(valores),
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._nombre_movimientos,
                            "Item": _a_dynamo(movimiento),
                            "ConditionExpression": "attribute_not_exists(clave_orden)",
                        }
                    },
                ]
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "TransactionCanceledException":
                raise
            actual = self._objeto(object_id)
            if actual is None:
                raise ErrorNoEncontrado(
                    f"No existe ningun objeto con id '{object_id}'."
                ) from exc
            raise ErrorConflicto(
                f"No hay existencias suficientes: quedan {int(actual.get('cantidad', 0))} piezas."
            ) from exc

        return _publico(self._objeto(object_id) or {})

    def listar_por_objeto(
        self, object_id: str, limite: int, cursor: dict | None = None
    ) -> tuple[list[dict], dict | None]:
        parametros: dict = {
            "KeyConditionExpression": Key("object_id").eq(object_id),
            # Del movimiento mas reciente al mas viejo.
            "ScanIndexForward": False,
            "Limit": limite,
        }
        if cursor:
            parametros["ExclusiveStartKey"] = cursor
        respuesta = _ejecutar(self._tabla.query, parametros)
        return respuesta.get("Items", []), respuesta.get("LastEvaluatedKey")


class RepositorioBusquedas:
    """Cronometro de las localizaciones, para el indicador de tiempo."""

    MAXIMO_PAGINAS_RESUMEN = 5

    def __init__(self, nombre_tabla: str | None = None, indice: str | None = None):
        self._nombre_tabla = nombre_tabla or config.tabla_busquedas()
        self._indice = indice or config.indice_busquedas_objeto()
        self._tabla = _recurso_dynamodb().Table(self._nombre_tabla)

    def abrir(self, busqueda: dict) -> dict:
        self._tabla.put_item(Item=busqueda)
        return busqueda

    def registrar_control(self, busqueda: dict) -> dict:
        self._tabla.put_item(Item=busqueda)
        return busqueda

    def _cerrar(self, item: dict, cerrada_por: str) -> dict:
        confirmada_en = ahora_iso_preciso()
        duracion = metricas.duracion_ms(item.get("iniciada_en", ""), confirmada_en)
        try:
            respuesta = self._tabla.update_item(
                Key={"busqueda_id": item["busqueda_id"]},
                UpdateExpression=(
                    "SET confirmada_en = :c, duracion_ms = :d, cerrada_por = :p"
                ),
                # Solo se cierra si sigue abierta: dos confirmaciones simultaneas
                # no pueden sobrescribir la duracion ya medida.
                ConditionExpression="confirmada_en = :vacio",
                ExpressionAttributeValues={
                    ":c": confirmada_en,
                    ":d": duracion,
                    ":p": cerrada_por,
                    ":vacio": "",
                },
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorConflicto("Esta busqueda ya estaba confirmada.") from exc
            raise
        return respuesta["Attributes"]

    def confirmar(self, busqueda_id: str, cerrada_por: str) -> dict:
        item = self._tabla.get_item(Key={"busqueda_id": busqueda_id}).get("Item")
        if not item:
            raise ErrorNoEncontrado(f"No existe ninguna busqueda con id '{busqueda_id}'.")
        if item.get("confirmada_en"):
            raise ErrorConflicto("Esta busqueda ya estaba confirmada.")
        return self._cerrar(item, cerrada_por)

    def cerrar_por_objeto(self, object_id: str, cerrada_por: str) -> dict | None:
        respuesta = _ejecutar(
            self._tabla.query,
            {
                "IndexName": self._indice,
                "KeyConditionExpression": Key("object_id").eq(object_id),
                "FilterExpression": Attr("confirmada_en").eq(""),
                "ScanIndexForward": False,
                "Limit": 10,
            },
        )
        abiertas = respuesta.get("Items", [])
        return self._cerrar(abiertas[0], cerrada_por) if abiertas else None

    def listar(self, limite: int) -> list[dict]:
        items: list[dict] = []
        parametros: dict = {"Limit": limite}
        for _ in range(self.MAXIMO_PAGINAS_RESUMEN):
            respuesta = _ejecutar(self._tabla.scan, parametros)
            items += respuesta.get("Items", [])
            cursor = respuesta.get("LastEvaluatedKey")
            if not cursor or len(items) >= limite:
                break
            parametros = {**parametros, "ExclusiveStartKey": cursor}
        return items[:limite]


class RepositorioCategorias:
    def __init__(self, nombre_tabla: str | None = None):
        self._nombre_tabla = nombre_tabla or config.tabla_categorias()
        self._tabla = _recurso_dynamodb().Table(self._nombre_tabla)

    def existe(self, categoria_id: str) -> bool:
        respuesta = self._tabla.get_item(
            Key={"categoria_id": categoria_id}, ProjectionExpression="categoria_id"
        )
        return "Item" in respuesta

    def crear(self, categoria: dict) -> dict:
        try:
            self._tabla.put_item(
                Item=categoria, ConditionExpression="attribute_not_exists(categoria_id)"
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorConflicto(
                    f"Ya existe una categoria con id '{categoria['categoria_id']}'."
                ) from exc
            raise
        return categoria

    def actualizar(self, categoria_id: str, cambios: dict) -> dict:
        nombres = {f"#c{i}": campo for i, campo in enumerate(cambios)}
        valores = {f":v{i}": valor for i, valor in enumerate(cambios.values())}
        asignaciones = ", ".join(f"{n} = {v}" for n, v in zip(nombres, valores))
        try:
            respuesta = self._tabla.update_item(
                Key={"categoria_id": categoria_id},
                UpdateExpression="SET " + asignaciones,
                ExpressionAttributeNames=nombres,
                ExpressionAttributeValues=valores,
                ConditionExpression="attribute_exists(categoria_id)",
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorNoEncontrado(
                    f"No existe ninguna categoria con id '{categoria_id}'."
                ) from exc
            raise
        return respuesta["Attributes"]

    def eliminar(self, categoria_id: str) -> dict:
        try:
            respuesta = self._tabla.delete_item(
                Key={"categoria_id": categoria_id},
                ConditionExpression="attribute_exists(categoria_id)",
                ReturnValues="ALL_OLD",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorNoEncontrado(
                    f"No existe ninguna categoria con id '{categoria_id}'."
                ) from exc
            raise
        return respuesta["Attributes"]

    def listar(
        self, limite: int, cursor: dict | None = None
    ) -> tuple[list[dict], dict | None]:
        parametros: dict = {"Limit": limite}
        if cursor:
            parametros["ExclusiveStartKey"] = cursor
        respuesta = _ejecutar(self._tabla.scan, parametros)
        return respuesta.get("Items", []), respuesta.get("LastEvaluatedKey")
