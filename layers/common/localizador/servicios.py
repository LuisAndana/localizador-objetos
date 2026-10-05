"""Casos de uso. Idénticos para Lambda (AWS) y para el servidor local (FastAPI).

Los adaptadores de entrada solo extraen parámetros de la petición; toda regla
de negocio y validación de contenido vive aquí o en `validacion.py`.
"""

import re
import time
import uuid

from . import metricas, paginacion, plano, validacion, vision
from .errores import ErrorConflicto, ErrorNoEncontrado, ErrorValidacion
from .modelos import Busqueda, Movimiento, Objeto, OrdenLed, ahora_iso_preciso
from .puertos import (
    PuertoBusquedas,
    PuertoCategorias,
    PuertoFotos,
    PuertoIdentificaciones,
    PuertoMovimientos,
    PuertoObjetos,
    PuertoPublicador,
    PuertoReconocimiento,
)

LIMITE_BUSQUEDAS_RESUMEN = 500
BUSQUEDAS_RECIENTES = 10


class ServicioObjetos:
    def __init__(self, repositorio: PuertoObjetos, categorias: PuertoCategorias | None = None):
        self._repositorio = repositorio
        # Solo lo necesitan crear y actualizar, para no aceptar categorias inexistentes.
        self._categorias = categorias

    def listar(
        self,
        categoria: str | None,
        limite: int,
        cursor: dict | None,
        busqueda: str | None = None,
    ) -> dict:
        if categoria:
            categoria = validacion.identificador(categoria, "categoria")
        termino = validacion.termino_busqueda(busqueda)
        if termino:
            elementos, ultima = self._repositorio.buscar(termino, categoria, limite, cursor)
        elif categoria:
            elementos, ultima = self._repositorio.listar_por_categoria(categoria, limite, cursor)
        else:
            elementos, ultima = self._repositorio.listar_todos(limite, cursor)
        return {**paginacion.pagina(elementos, ultima), "categoria": categoria, "q": termino}

    def obtener(self, object_id: str) -> dict:
        return self._repositorio.obtener(object_id)

    def crear(self, cuerpo: dict) -> dict:
        datos = validacion.objeto_nuevo(cuerpo)
        self._exigir_categoria(datos["categoria"])
        self._exigir_led_libre(datos["almacen_id"], datos["posicion_led"], datos.get("object_id"))
        return self._repositorio.crear(datos)

    def eliminar(self, object_id: str) -> dict:
        """El historial de movimientos y busquedas se conserva: es la auditoria."""
        return self._repositorio.eliminar(validacion.identificador(object_id, "object_id"))

    def _exigir_categoria(self, categoria: str) -> None:
        if self._categorias is not None and not self._categorias.existe(categoria):
            raise ErrorValidacion(
                f"La categoria '{categoria}' no existe. Dala de alta primero en Categorias.",
                {"campo": "categoria"},
            )

    def actualizar(self, object_id: str, cuerpo: dict) -> dict:
        cambios = validacion.objeto_actualizacion(cuerpo)
        if "categoria" in cambios:
            self._exigir_categoria(cambios["categoria"])
        if "posicion_led" in cambios or "almacen_id" in cambios:
            # Solo se relee el objeto cuando el cambio puede mover el LED de sitio.
            actual = self._repositorio.obtener(object_id)
            self._exigir_led_libre(
                cambios.get("almacen_id", actual["almacen_id"]),
                cambios.get("posicion_led", actual["posicion_led"]),
                object_id,
            )
        return self._repositorio.actualizar(object_id, cambios)

    def _exigir_led_libre(
        self, almacen_id: str, posicion_led: int, object_id: str | None
    ) -> None:
        """Dos objetos en la misma posicion se encenderian juntos: la tira no los
        distingue, asi que la ubicacion fisica dejaria de ser univoca."""
        for otro in self._repositorio.listar_por_almacen(almacen_id):
            if otro.get("posicion_led") != posicion_led:
                continue
            if object_id is not None and otro.get("object_id") == object_id:
                continue
            ocupante = otro.get("nombre") or otro.get("object_id", "otro objeto")
            raise ErrorConflicto(
                f"La posicion LED {posicion_led} ya la ocupa '{ocupante}' en este almacen.",
                {"campo": "posicion_led", "object_id": otro.get("object_id")},
            )


class ServicioCategorias:
    def __init__(self, repositorio: PuertoCategorias, objetos: PuertoObjetos | None = None):
        self._repositorio = repositorio
        # Solo lo necesita eliminar: para no dejar objetos con una categoria huerfana.
        self._objetos = objetos

    def listar(self, limite: int, cursor: dict | None) -> dict:
        elementos, ultima = self._repositorio.listar(limite, cursor)
        return paginacion.pagina(elementos, ultima)

    def crear(self, cuerpo: dict) -> dict:
        return self._repositorio.crear(validacion.categoria_nueva(cuerpo))

    def actualizar(self, categoria_id: str, cuerpo: dict) -> dict:
        return self._repositorio.actualizar(
            validacion.identificador(categoria_id, "categoria_id"),
            validacion.categoria_actualizacion(cuerpo),
        )

    def eliminar(self, categoria_id: str) -> dict:
        categoria_id = validacion.identificador(categoria_id, "categoria_id")
        if self._objetos is None:
            raise RuntimeError("ServicioCategorias.eliminar necesita el repositorio de objetos.")
        if self._objetos.hay_en_categoria(categoria_id):
            raise ErrorConflicto(
                "La categoria todavia tiene objetos. Muevelos a otra categoria antes de eliminarla.",
                {"categoria_id": categoria_id},
            )
        return self._repositorio.eliminar(categoria_id)


class ServicioBusquedas:
    """Cronometra las localizaciones para medir el indicador de tiempo del acta."""

    def __init__(self, repositorio: PuertoBusquedas):
        self._repositorio = repositorio

    def abrir(self, object_id: str) -> dict:
        busqueda = Busqueda(busqueda_id=str(uuid.uuid4()), object_id=object_id)
        return self._repositorio.abrir(busqueda.a_item())

    def confirmar(self, busqueda_id: str, cerrada_por: str = "app") -> dict:
        return self._repositorio.confirmar(
            validacion.identificador(busqueda_id, "busqueda_id"), cerrada_por
        )

    def cerrar_por_objeto(self, object_id: str) -> dict | None:
        """La salida del material confirma que el operador ya lo encontro."""
        return self._repositorio.cerrar_por_objeto(object_id, "salida")

    def registrar_control(self, cuerpo: dict) -> dict:
        datos = validacion.busqueda_control(cuerpo)
        ahora = ahora_iso_preciso()
        busqueda = Busqueda(
            busqueda_id=str(uuid.uuid4()),
            object_id=datos["object_id"],
            modo="control",
            iniciada_en=ahora,
            confirmada_en=ahora,
            duracion_ms=datos["duracion_ms"],
            cerrada_por="app",
        )
        return self._repositorio.registrar_control(busqueda.a_item())

    def resumen(self) -> dict:
        busquedas = self._repositorio.listar(LIMITE_BUSQUEDAS_RESUMEN)
        confirmadas = [b for b in busquedas if b.get("confirmada_en")]
        recientes = sorted(
            confirmadas, key=lambda b: b.get("confirmada_en", ""), reverse=True
        )[:BUSQUEDAS_RECIENTES]
        return {**metricas.resumir(busquedas), "recientes": recientes}


class ServicioMovimientos:
    """Entradas y salidas de material. Cada movimiento ajusta la cantidad del objeto."""

    def __init__(self, repositorio: PuertoMovimientos, busquedas: PuertoBusquedas):
        self._repositorio = repositorio
        self._busquedas = busquedas

    def registrar(self, cuerpo: dict) -> dict:
        datos = validacion.movimiento_nuevo(cuerpo)
        movimiento = Movimiento(movimiento_id=str(uuid.uuid4()), **datos)
        # El repositorio aplica el delta y escribe el historial en una sola
        # operacion: si el objeto no existe o la salida deja negativo, no se
        # escribe nada.
        objeto = self._repositorio.registrar(movimiento.a_item(), movimiento.delta)
        respuesta = {"movimiento": movimiento.a_item(), "objeto": objeto}
        if movimiento.tipo == "salida":
            # Retirar el material cierra el cronometro: es la senal mas confiable
            # de que la busqueda termino, y no depende de que el operador pulse nada.
            cerrada = self._busquedas.cerrar_por_objeto(
                movimiento.object_id, "salida"
            )
            if cerrada:
                respuesta["busqueda"] = cerrada
        return respuesta

    def listar(self, object_id: str, limite: int, cursor: dict | None) -> dict:
        object_id = validacion.identificador(object_id, "object_id")
        elementos, ultima = self._repositorio.listar_por_objeto(object_id, limite, cursor)
        return {**paginacion.pagina(elementos, ultima), "object_id": object_id}


class ServicioPlano:
    """Mapa 2D del almacen: pasillos, anaqueles y niveles con lo que hay en cada uno."""

    def __init__(self, repositorio: PuertoObjetos):
        self._repositorio = repositorio

    def almacenes(self) -> dict:
        return {"elementos": self._repositorio.resumen_almacenes()}

    def obtener(self, almacen_id: str) -> dict:
        almacen_id = validacion.identificador(almacen_id, "almacen_id")
        objetos = self._repositorio.listar_por_almacen(almacen_id)
        if not objetos:
            # Un almacen existe porque hay objetos ubicados en el; sin objetos no
            # hay plano que dibujar y devolver uno vacio ocultaria un id mal escrito.
            raise ErrorNoEncontrado(f"No hay objetos registrados en el almacen '{almacen_id}'.")
        return plano.construir(almacen_id, objetos)


class ServicioLocalizacion:
    """Busca el objeto y ordena al nodo de su almacén encender el LED."""

    def __init__(
        self,
        repositorio: PuertoObjetos,
        publicador: PuertoPublicador,
        busquedas: PuertoBusquedas,
    ):
        self._repositorio = repositorio
        self._publicador = publicador
        self._busquedas = busquedas

    def localizar(self, object_id: str, duracion_segundos: int) -> dict:
        objeto = Objeto.desde_item(self._repositorio.obtener(object_id))
        orden = OrdenLed(
            posicion_led=objeto.ubicacion.posicion_led,
            color_indicador=objeto.color_indicador,
            duracion_segundos=duracion_segundos,
            object_id=objeto.object_id,
        )
        # El cronometro arranca aqui, antes de publicar: el tiempo que mide el
        # indicador es el que espera la persona, no el que tarda el broker.
        busqueda = Busqueda(busqueda_id=str(uuid.uuid4()), object_id=objeto.object_id)
        topic = self._publicador.publicar(objeto.ubicacion.almacen_id, orden)
        self._busquedas.abrir(busqueda.a_item())
        return {
            "mensaje": "Orden de localizacion enviada al nodo del almacen.",
            "object_id": objeto.object_id,
            "nombre": objeto.nombre,
            "topic": topic,
            "busqueda_id": busqueda.busqueda_id,
            "ubicacion": {
                "almacen_id": objeto.ubicacion.almacen_id,
                "pasillo": objeto.ubicacion.pasillo,
                "anaquel": objeto.ubicacion.anaquel,
                "nivel": objeto.ubicacion.nivel,
                "columna": objeto.ubicacion.columna,
                "descripcion": objeto.ubicacion.descripcion(),
            },
            "orden_led": orden.a_payload(),
        }


class ServicioIdentificacion:
    """Identificacion de un objeto por foto (Amazon Rekognition).

    1. `solicitar`: crea la solicitud y da una URL prefirmada; el navegador sube
       la foto directo a S3 (la imagen no pasa por la API).
    2. `procesar`: la dispara el evento de S3 al llegar la foto; pide a
       Rekognition etiquetas y texto, y guarda la propuesta.
    3. `obtener`: la app consulta hasta que la propuesta esta lista.
    """

    PREFIJO_FOTOS = "fotos/"
    # Solo claves que este servicio pudo haber generado: fotos/<uuid>.jpg
    REGEX_CLAVE = re.compile(r"^fotos/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jpg$")
    # Igual que la regla de ciclo de vida del bucket: las fotos se borran a los 30 dias.
    RETENCION_SEGUNDOS = 30 * 24 * 3600
    LIMITE_CATEGORIAS = 200

    def __init__(
        self,
        repositorio: PuertoIdentificaciones,
        fotos: PuertoFotos | None = None,
        reconocimiento: PuertoReconocimiento | None = None,
        categorias: PuertoCategorias | None = None,
    ):
        self._repositorio = repositorio
        self._fotos = fotos
        self._reconocimiento = reconocimiento
        self._categorias = categorias

    def solicitar(self, usuario: str | None) -> dict:
        identificacion_id = str(uuid.uuid4())
        clave = f"{self.PREFIJO_FOTOS}{identificacion_id}.jpg"
        self._repositorio.crear(
            {
                "identificacion_id": identificacion_id,
                "estado": "pendiente",
                "clave_foto": clave,
                "solicitada_por": usuario or "",
                "creada_en": ahora_iso_preciso(),
                # TTL de DynamoDB: la solicitud desaparece junto con su foto.
                "expira_en": int(time.time()) + self.RETENCION_SEGUNDOS,
            }
        )
        return {"identificacion_id": identificacion_id, "subida": self._fotos.url_subida(clave)}

    def obtener(self, identificacion_id: str, usuario: str | None) -> dict:
        identificacion_id = validacion.identificador(identificacion_id, "identificacion_id")
        item = self._repositorio.obtener(identificacion_id)
        # Cada quien ve solo sus fotos. Se responde 404 (no 403) para no revelar
        # que el id existe.
        if usuario and item.get("solicitada_por") != usuario:
            raise ErrorNoEncontrado(f"No existe ninguna identificacion con id '{identificacion_id}'.")
        return {k: v for k, v in item.items() if k not in ("solicitada_por", "expira_en", "clave_foto")}

    def procesar(self, clave: str) -> str | None:
        """Devuelve el id procesado, o None si la clave no es de este servicio."""
        coincidencia = self.REGEX_CLAVE.match(clave)
        if not coincidencia:
            return None
        identificacion_id = coincidencia.group(1)
        try:
            etiquetas, textos = self._reconocimiento.analizar(clave)
            categorias = self._ids_categorias()
            propuesta = vision.proponer(etiquetas, textos, categorias)
        except Exception:
            self._repositorio.fallar(identificacion_id, "No se pudo analizar la foto. Toma otra.")
            raise
        self._repositorio.completar(identificacion_id, propuesta)
        return identificacion_id

    def _ids_categorias(self) -> set[str]:
        if self._categorias is None:
            return set()
        elementos, _ = self._categorias.listar(self.LIMITE_CATEGORIAS, None)
        return {c["categoria_id"] for c in elementos}
