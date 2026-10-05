"""Infraestructura local: SQLite hace de DynamoDB y una tabla de órdenes hace de IoT Core.

Cumple los mismos contratos (`localizador.puertos`) que los adaptadores de AWS,
con la misma semántica de errores (404, 409, cursor inválido → 400) y la misma
paginación por cursor, para que el frontend no note la diferencia.
"""

import json
import logging
import math
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from localizador import metricas, validacion
from localizador.errores import ErrorConflicto, ErrorNoEncontrado, ErrorValidacion
from localizador.modelos import PLANTILLA_TOPIC, OrdenLed, ahora_iso, ahora_iso_preciso

from .semilla import sembrar

logger = logging.getLogger("localizador.local")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS categorias (
    categoria_id TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    descripcion  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS objetos (
    object_id            TEXT PRIMARY KEY,
    nombre               TEXT NOT NULL,
    categoria            TEXT NOT NULL,
    almacen_id           TEXT NOT NULL,
    pasillo              TEXT NOT NULL,
    anaquel              TEXT NOT NULL,
    nivel                TEXT NOT NULL,
    columna              TEXT NOT NULL DEFAULT 'A',
    posicion_led         INTEGER NOT NULL,
    color_indicador      TEXT NOT NULL,
    cantidad             INTEGER NOT NULL DEFAULT 0,
    ultima_actualizacion TEXT NOT NULL
);
-- Equivalente al GSI categoria-index de DynamoDB.
CREATE INDEX IF NOT EXISTS ix_objetos_categoria ON objetos (categoria, nombre, object_id);

-- Mismo diseno que la tabla de DynamoDB: particion por objeto y orden por
-- clave_orden (marca de tiempo + id), para leer el historial de un objeto sin
-- recorrer toda la tabla.
CREATE TABLE IF NOT EXISTS movimientos (
    object_id     TEXT NOT NULL,
    clave_orden   TEXT NOT NULL,
    movimiento_id TEXT NOT NULL,
    tipo          TEXT NOT NULL,
    cantidad      INTEGER NOT NULL,
    origen        TEXT NOT NULL DEFAULT 'app',
    motivo        TEXT NOT NULL DEFAULT '',
    referencia    TEXT NOT NULL DEFAULT '',
    registrado_en TEXT NOT NULL,
    PRIMARY KEY (object_id, clave_orden)
);

-- Cronometro de cada localizacion, para el indicador de tiempo del acta.
CREATE TABLE IF NOT EXISTS busquedas (
    busqueda_id   TEXT PRIMARY KEY,
    object_id     TEXT NOT NULL,
    modo          TEXT NOT NULL DEFAULT 'sistema',
    iniciada_en   TEXT NOT NULL,
    confirmada_en TEXT NOT NULL DEFAULT '',
    duracion_ms   INTEGER NOT NULL DEFAULT 0,
    cerrada_por   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_busquedas_objeto ON busquedas (object_id, iniciada_en);

CREATE TABLE IF NOT EXISTS ordenes_led (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    almacen_id        TEXT NOT NULL,
    topic             TEXT NOT NULL,
    object_id         TEXT NOT NULL,
    posicion_led      INTEGER NOT NULL,
    color_indicador   TEXT NOT NULL,
    duracion_segundos INTEGER NOT NULL,
    emitido_en        TEXT NOT NULL,
    expira_en         REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ordenes_almacen ON ordenes_led (almacen_id, expira_en);
"""

COLUMNAS_OBJETO = (
    "object_id",
    "nombre",
    "categoria",
    "almacen_id",
    "pasillo",
    "anaquel",
    "nivel",
    "columna",
    "posicion_led",
    "color_indicador",
    "cantidad",
    "ultima_actualizacion",
)
COLUMNAS_BUSQUEDA = (
    "busqueda_id",
    "object_id",
    "modo",
    "iniciada_en",
    "confirmada_en",
    "duracion_ms",
    "cerrada_por",
)
COLUMNAS_MOVIMIENTO = (
    "object_id",
    "clave_orden",
    "movimiento_id",
    "tipo",
    "cantidad",
    "origen",
    "motivo",
    "referencia",
    "registrado_en",
)
MENSAJE_CURSOR_INVALIDO = "Los parametros de paginacion no son validos para esta consulta."


class BaseLocal:
    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)

    @contextmanager
    def conexion(self) -> Iterator[sqlite3.Connection]:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.ruta, timeout=5)
        con.row_factory = sqlite3.Row
        # La misma normalizacion que guarda DynamoDB en 'nombre_busqueda', aplicada
        # al vuelo: SQLite no compara sin acentos por su cuenta.
        con.create_function("normalizar", 1, validacion.normalizar_busqueda, deterministic=True)
        try:
            with con:  # commit al salir, rollback si hay excepción
                yield con
        finally:
            con.close()

    @staticmethod
    def _migrar(con: sqlite3.Connection) -> None:
        """Las bases creadas antes de las entradas y salidas no traen 'cantidad'.

        CREATE TABLE IF NOT EXISTS no altera una tabla que ya existe, asi que la
        columna se agrega aqui para no obligar a borrar datos_local/.
        """
        columnas = {fila["name"] for fila in con.execute("PRAGMA table_info(objetos)")}
        if "cantidad" not in columnas:
            con.execute("ALTER TABLE objetos ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 0")
            logger.info("Base local migrada: columna 'cantidad' agregada a objetos.")
        if "columna" not in columnas:
            con.execute("ALTER TABLE objetos ADD COLUMN columna TEXT NOT NULL DEFAULT 'A'")
            BaseLocal._repartir_columnas(con)
            logger.info("Base local migrada: los objetos se acomodaron en columnas del anaquel.")

    @staticmethod
    def _repartir_columnas(con: sqlite3.Connection) -> None:
        """Los objetos que compartian nivel se reparten en columnas A, B, C... por
        el orden de su LED, que es como corre la tira de izquierda a derecha.
        Sin esto, al migrar quedarian todos amontonados en la columna A."""
        filas = con.execute(
            """SELECT object_id, almacen_id, pasillo, anaquel, nivel FROM objetos
               ORDER BY almacen_id, pasillo, anaquel, nivel, posicion_led"""
        ).fetchall()
        lugar_anterior, indice = None, 0
        for fila in filas:
            lugar = (fila["almacen_id"], fila["pasillo"], fila["anaquel"], fila["nivel"])
            indice = indice + 1 if lugar == lugar_anterior else 0
            lugar_anterior = lugar
            columna = chr(ord("A") + indice) if indice < 26 else str(indice + 1)
            con.execute("UPDATE objetos SET columna = ? WHERE object_id = ?", (columna, fila["object_id"]))

    def inicializar(self, con_semilla: bool = True) -> None:
        with self.conexion() as con:
            con.executescript(ESQUEMA)
            self._migrar(con)
            vacia = con.execute("SELECT COUNT(*) FROM objetos").fetchone()[0] == 0
            if con_semilla and vacia:
                sembrar(con)
                logger.info("Base local sembrada con datos de demostración.")


def _validar_cursor(cursor: dict | None, claves: tuple[str, ...]) -> dict | None:
    if cursor is None:
        return None
    if set(cursor) != set(claves) or not all(isinstance(cursor[k], str) for k in claves):
        raise ErrorValidacion(MENSAJE_CURSOR_INVALIDO)
    return cursor


def _recortar(filas: list[sqlite3.Row], limite: int, claves: tuple[str, ...]):
    """Se piden limite+1 filas: si sobra una, hay página siguiente."""
    elementos = [dict(f) for f in filas[:limite]]
    if len(filas) > limite:
        ultimo = elementos[-1]
        return elementos, {k: ultimo[k] for k in claves}
    return elementos, None


class RepositorioObjetosSqlite:
    def __init__(self, base: BaseLocal):
        self._base = base

    def obtener(self, object_id: str) -> dict:
        with self._base.conexion() as con:
            fila = con.execute("SELECT * FROM objetos WHERE object_id = ?", (object_id,)).fetchone()
        if fila is None:
            raise ErrorNoEncontrado(f"No existe ningun objeto con id '{object_id}'.")
        return dict(fila)

    def crear(self, datos: dict) -> dict:
        item = {
            **datos,
            "object_id": datos.get("object_id") or str(uuid.uuid4()),
            "ultima_actualizacion": ahora_iso(),
        }
        marcadores = ", ".join("?" for _ in COLUMNAS_OBJETO)
        try:
            with self._base.conexion() as con:
                con.execute(
                    f"INSERT INTO objetos ({', '.join(COLUMNAS_OBJETO)}) VALUES ({marcadores})",
                    [item[c] for c in COLUMNAS_OBJETO],
                )
        except sqlite3.IntegrityError as exc:
            raise ErrorConflicto(f"Ya existe un objeto con id '{item['object_id']}'.") from exc
        return item

    def actualizar(self, object_id: str, cambios: dict) -> dict:
        # Los nombres de columna salen de una lista blanca, nunca del cliente:
        # por eso es seguro interpolarlos; los valores siempre van como parámetros.
        if not cambios or not set(cambios) <= set(validacion.CAMPOS_ACTUALIZABLES):
            raise ErrorValidacion("El cuerpo contiene campos no permitidos.")
        cambios = {**cambios, "ultima_actualizacion": ahora_iso()}
        asignaciones = ", ".join(f"{columna} = ?" for columna in cambios)
        with self._base.conexion() as con:
            cursor = con.execute(
                f"UPDATE objetos SET {asignaciones} WHERE object_id = ?",
                [*cambios.values(), object_id],
            )
            if cursor.rowcount == 0:
                raise ErrorNoEncontrado(f"No existe ningun objeto con id '{object_id}'.")
        return self.obtener(object_id)

    def listar_por_categoria(self, categoria: str, limite: int, cursor: dict | None = None):
        claves = ("nombre", "object_id")
        desde = _validar_cursor(cursor, claves)
        sql = "SELECT * FROM objetos WHERE categoria = ?"
        parametros: list = [categoria]
        if desde:
            sql += " AND (nombre, object_id) > (?, ?)"
            parametros += [desde["nombre"], desde["object_id"]]
        sql += " ORDER BY nombre, object_id LIMIT ?"
        parametros.append(limite + 1)
        with self._base.conexion() as con:
            filas = con.execute(sql, parametros).fetchall()
        return _recortar(filas, limite, claves)

    def eliminar(self, object_id: str) -> dict:
        with self._base.conexion() as con:
            fila = con.execute("SELECT * FROM objetos WHERE object_id = ?", (object_id,)).fetchone()
            if fila is None:
                raise ErrorNoEncontrado(f"No existe ningun objeto con id '{object_id}'.")
            if fila["cantidad"] > 0:
                raise ErrorConflicto(
                    f"Al objeto le quedan {fila['cantidad']} piezas. "
                    "Registra su salida antes de eliminarlo.",
                    {"cantidad": fila["cantidad"]},
                )
            con.execute("DELETE FROM objetos WHERE object_id = ?", (object_id,))
        return dict(fila)

    @staticmethod
    def _patron_like(termino: str) -> str:
        """'%' y '_' son comodines de LIKE: se escapan para buscarlos literalmente."""
        escapado = termino.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return f"%{escapado}%"

    def buscar(self, termino: str, categoria: str | None, limite: int, cursor: dict | None = None):
        claves = ("nombre", "object_id")
        desde = _validar_cursor(cursor, claves)
        patron = self._patron_like(termino)
        sql = (
            "SELECT * FROM objetos "
            "WHERE (normalizar(nombre) LIKE ? ESCAPE '\\' OR object_id LIKE ? ESCAPE '\\')"
        )
        parametros: list = [patron, patron]
        if categoria:
            sql += " AND categoria = ?"
            parametros.append(categoria)
        if desde:
            sql += " AND (nombre, object_id) > (?, ?)"
            parametros += [desde["nombre"], desde["object_id"]]
        sql += " ORDER BY nombre, object_id LIMIT ?"
        parametros.append(limite + 1)
        with self._base.conexion() as con:
            filas = con.execute(sql, parametros).fetchall()
        return _recortar(filas, limite, claves)

    def hay_en_categoria(self, categoria: str) -> bool:
        with self._base.conexion() as con:
            fila = con.execute(
                "SELECT 1 FROM objetos WHERE categoria = ? LIMIT 1", (categoria,)
            ).fetchone()
        return fila is not None

    def listar_por_almacen(self, almacen_id: str) -> list[dict]:
        with self._base.conexion() as con:
            filas = con.execute(
                "SELECT * FROM objetos WHERE almacen_id = ? ORDER BY pasillo, anaquel, nivel, columna",
                (almacen_id,),
            ).fetchall()
        return [dict(f) for f in filas]

    def resumen_almacenes(self) -> list[dict]:
        with self._base.conexion() as con:
            filas = con.execute(
                """SELECT almacen_id,
                          COUNT(*) AS total_objetos,
                          COUNT(DISTINCT pasillo) AS total_pasillos
                   FROM objetos GROUP BY almacen_id ORDER BY almacen_id"""
            ).fetchall()
        return [dict(f) for f in filas]

    def listar_todos(self, limite: int, cursor: dict | None = None):
        claves = ("object_id",)
        desde = _validar_cursor(cursor, claves)
        sql = "SELECT * FROM objetos"
        parametros: list = []
        if desde:
            sql += " WHERE object_id > ?"
            parametros.append(desde["object_id"])
        sql += " ORDER BY object_id LIMIT ?"
        parametros.append(limite + 1)
        with self._base.conexion() as con:
            filas = con.execute(sql, parametros).fetchall()
        return _recortar(filas, limite, claves)


class RepositorioMovimientosSqlite:
    """Entradas y salidas. El ajuste de cantidad y el historial van en la misma
    transaccion: si algo falla, no queda ni el movimiento ni el descuento."""

    def __init__(self, base: BaseLocal):
        self._base = base

    def registrar(self, movimiento: dict, delta: int) -> dict:
        object_id = movimiento["object_id"]
        with self._base.conexion() as con:
            # La condicion 'cantidad + delta >= 0' hace el trabajo de la
            # ConditionExpression de DynamoDB: evita dejar existencias negativas
            # sin leer antes de escribir.
            cursor = con.execute(
                """UPDATE objetos
                      SET cantidad = cantidad + ?, ultima_actualizacion = ?
                    WHERE object_id = ? AND cantidad + ? >= 0""",
                (delta, ahora_iso(), object_id, delta),
            )
            if cursor.rowcount == 0:
                fila = con.execute(
                    "SELECT cantidad FROM objetos WHERE object_id = ?", (object_id,)
                ).fetchone()
                if fila is None:
                    raise ErrorNoEncontrado(f"No existe ningun objeto con id '{object_id}'.")
                raise ErrorConflicto(
                    f"No hay existencias suficientes: quedan {fila['cantidad']} piezas."
                )
            marcadores = ", ".join("?" for _ in COLUMNAS_MOVIMIENTO)
            con.execute(
                f"INSERT INTO movimientos ({', '.join(COLUMNAS_MOVIMIENTO)}) "
                f"VALUES ({marcadores})",
                [movimiento[c] for c in COLUMNAS_MOVIMIENTO],
            )
            objeto = con.execute(
                "SELECT * FROM objetos WHERE object_id = ?", (object_id,)
            ).fetchone()
        return dict(objeto)

    def listar_por_objeto(self, object_id: str, limite: int, cursor: dict | None = None):
        claves = ("clave_orden",)
        desde = _validar_cursor(cursor, claves)
        # Descendente: el historial se lee del movimiento mas reciente al mas viejo.
        sql = "SELECT * FROM movimientos WHERE object_id = ?"
        parametros: list = [object_id]
        if desde:
            sql += " AND clave_orden < ?"
            parametros.append(desde["clave_orden"])
        sql += " ORDER BY clave_orden DESC LIMIT ?"
        parametros.append(limite + 1)
        with self._base.conexion() as con:
            filas = con.execute(sql, parametros).fetchall()
        return _recortar(filas, limite, claves)


class RepositorioBusquedasSqlite:
    """Cronometro de las localizaciones (equivalente a la tabla Busquedas)."""

    def __init__(self, base: BaseLocal):
        self._base = base

    def _insertar(self, busqueda: dict) -> dict:
        marcadores = ", ".join("?" for _ in COLUMNAS_BUSQUEDA)
        with self._base.conexion() as con:
            con.execute(
                f"INSERT INTO busquedas ({', '.join(COLUMNAS_BUSQUEDA)}) VALUES ({marcadores})",
                [busqueda[c] for c in COLUMNAS_BUSQUEDA],
            )
        return busqueda

    def abrir(self, busqueda: dict) -> dict:
        return self._insertar(busqueda)

    def registrar_control(self, busqueda: dict) -> dict:
        return self._insertar(busqueda)

    @staticmethod
    def _cerrar(con: sqlite3.Connection, fila: dict, cerrada_por: str) -> dict:
        confirmada_en = ahora_iso_preciso()
        duracion = metricas.duracion_ms(fila["iniciada_en"], confirmada_en)
        con.execute(
            """UPDATE busquedas
                  SET confirmada_en = ?, duracion_ms = ?, cerrada_por = ?
                WHERE busqueda_id = ?""",
            (confirmada_en, duracion, cerrada_por, fila["busqueda_id"]),
        )
        return {
            **fila,
            "confirmada_en": confirmada_en,
            "duracion_ms": duracion,
            "cerrada_por": cerrada_por,
        }

    def confirmar(self, busqueda_id: str, cerrada_por: str) -> dict:
        with self._base.conexion() as con:
            fila = con.execute(
                "SELECT * FROM busquedas WHERE busqueda_id = ?", (busqueda_id,)
            ).fetchone()
            if fila is None:
                raise ErrorNoEncontrado(f"No existe ninguna busqueda con id '{busqueda_id}'.")
            if fila["confirmada_en"]:
                raise ErrorConflicto("Esta busqueda ya estaba confirmada.")
            return self._cerrar(con, dict(fila), cerrada_por)

    def cerrar_por_objeto(self, object_id: str, cerrada_por: str) -> dict | None:
        with self._base.conexion() as con:
            fila = con.execute(
                """SELECT * FROM busquedas
                    WHERE object_id = ? AND confirmada_en = ''
                    ORDER BY iniciada_en DESC LIMIT 1""",
                (object_id,),
            ).fetchone()
            if fila is None:
                return None
            return self._cerrar(con, dict(fila), cerrada_por)

    def listar(self, limite: int) -> list[dict]:
        with self._base.conexion() as con:
            filas = con.execute(
                "SELECT * FROM busquedas ORDER BY iniciada_en DESC LIMIT ?", (limite,)
            ).fetchall()
        return [dict(f) for f in filas]


class RepositorioCategoriasSqlite:
    def __init__(self, base: BaseLocal):
        self._base = base

    def _obtener(self, con: sqlite3.Connection, categoria_id: str) -> dict:
        fila = con.execute(
            "SELECT * FROM categorias WHERE categoria_id = ?", (categoria_id,)
        ).fetchone()
        if fila is None:
            raise ErrorNoEncontrado(f"No existe ninguna categoria con id '{categoria_id}'.")
        return dict(fila)

    def existe(self, categoria_id: str) -> bool:
        with self._base.conexion() as con:
            fila = con.execute(
                "SELECT 1 FROM categorias WHERE categoria_id = ?", (categoria_id,)
            ).fetchone()
        return fila is not None

    def crear(self, categoria: dict) -> dict:
        try:
            with self._base.conexion() as con:
                con.execute(
                    "INSERT INTO categorias (categoria_id, nombre, descripcion) VALUES (?, ?, ?)",
                    (categoria["categoria_id"], categoria["nombre"], categoria["descripcion"]),
                )
        except sqlite3.IntegrityError as exc:
            raise ErrorConflicto(
                f"Ya existe una categoria con id '{categoria['categoria_id']}'."
            ) from exc
        return categoria

    def actualizar(self, categoria_id: str, cambios: dict) -> dict:
        # Columnas de una lista blanca, nunca del cliente; los valores van como parametros.
        if not cambios or not set(cambios) <= set(validacion.CAMPOS_CATEGORIA_ACTUALIZABLES):
            raise ErrorValidacion("El cuerpo contiene campos no permitidos.")
        asignaciones = ", ".join(f"{columna} = ?" for columna in cambios)
        with self._base.conexion() as con:
            con.execute(
                f"UPDATE categorias SET {asignaciones} WHERE categoria_id = ?",
                [*cambios.values(), categoria_id],
            )
            return self._obtener(con, categoria_id)

    def eliminar(self, categoria_id: str) -> dict:
        with self._base.conexion() as con:
            categoria = self._obtener(con, categoria_id)
            con.execute("DELETE FROM categorias WHERE categoria_id = ?", (categoria_id,))
        return categoria

    def listar(self, limite: int, cursor: dict | None = None):
        claves = ("categoria_id",)
        desde = _validar_cursor(cursor, claves)
        sql = "SELECT * FROM categorias"
        parametros: list = []
        if desde:
            sql += " WHERE categoria_id > ?"
            parametros.append(desde["categoria_id"])
        sql += " ORDER BY categoria_id LIMIT ?"
        parametros.append(limite + 1)
        with self._base.conexion() as con:
            filas = con.execute(sql, parametros).fetchall()
        return _recortar(filas, limite, claves)


class PublicadorLedSqlite:
    """Hace de IoT Core: guarda la orden para que el simulador del nodo la reciba."""

    RETENCION_SEGUNDOS = 3600

    def __init__(self, base: BaseLocal):
        self._base = base

    def publicar(self, almacen_id: str, orden: OrdenLed) -> str:
        almacen_id = validacion.identificador(almacen_id, "almacen_id")
        topic = PLANTILLA_TOPIC.format(almacen_id=almacen_id)
        ahora = time.time()
        with self._base.conexion() as con:
            con.execute("DELETE FROM ordenes_led WHERE expira_en < ?", (ahora - self.RETENCION_SEGUNDOS,))
            con.execute(
                """INSERT INTO ordenes_led
                   (almacen_id, topic, object_id, posicion_led, color_indicador,
                    duracion_segundos, emitido_en, expira_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    almacen_id,
                    topic,
                    orden.object_id,
                    orden.posicion_led,
                    orden.color_indicador,
                    orden.duracion_segundos,
                    orden.emitido_en,
                    ahora + orden.duracion_segundos,
                ),
            )
        logger.info("[MQTT simulado] topic=%s payload=%s", topic, json.dumps(orden.a_payload()))
        return topic


def _tamano_tira(max_led: int | None) -> int:
    """Longitud visual de la tira: múltiplo de 30 LEDs, mínimo 60."""
    if max_led is None:
        return 60
    return max(60, math.ceil((max_led + 1) / 30) * 30)


class SimuladorNodos:
    """Lo que "vería" cada nodo ESP32 suscrito a almacen/{id}/led. Solo existe en local."""

    def __init__(self, base: BaseLocal):
        self._base = base

    def almacenes(self) -> list[dict]:
        with self._base.conexion() as con:
            filas = con.execute(
                """SELECT almacen_id, COUNT(*) AS total_objetos, MAX(posicion_led) AS max_led
                   FROM objetos GROUP BY almacen_id ORDER BY almacen_id"""
            ).fetchall()
        return [
            {
                "almacen_id": f["almacen_id"],
                "topic": PLANTILLA_TOPIC.format(almacen_id=f["almacen_id"]),
                "total_objetos": f["total_objetos"],
                "total_leds": _tamano_tira(f["max_led"]),
            }
            for f in filas
        ]

    def estado(self, almacen_id: str) -> dict:
        almacen_id = validacion.identificador(almacen_id, "almacen_id")
        ahora = time.time()
        with self._base.conexion() as con:
            max_led = con.execute(
                "SELECT MAX(posicion_led) FROM objetos WHERE almacen_id = ?", (almacen_id,)
            ).fetchone()[0]
            filas = con.execute(
                """SELECT o.posicion_led, o.color_indicador, o.object_id, o.duracion_segundos,
                          o.emitido_en, o.expira_en, obj.nombre
                   FROM ordenes_led o
                   LEFT JOIN objetos obj ON obj.object_id = o.object_id
                   WHERE o.almacen_id = ? AND o.expira_en > ?
                   ORDER BY o.id DESC""",
                (almacen_id, ahora),
            ).fetchall()

        # Si llegan dos órdenes para el mismo LED, manda la más reciente (como en la tira real).
        activos: dict[int, dict] = {}
        for f in filas:
            if f["posicion_led"] not in activos:
                activos[f["posicion_led"]] = {
                    "posicion_led": f["posicion_led"],
                    "color_indicador": f["color_indicador"],
                    "object_id": f["object_id"],
                    "nombre": f["nombre"],
                    "duracion_segundos": f["duracion_segundos"],
                    "emitido_en": f["emitido_en"],
                    "segundos_restantes": round(f["expira_en"] - ahora, 1),
                }

        mayor = max([max_led or 0, *activos]) if (max_led is not None or activos) else None
        return {
            "almacen_id": almacen_id,
            "topic": PLANTILLA_TOPIC.format(almacen_id=almacen_id),
            "total_leds": _tamano_tira(mayor),
            "activos": sorted(activos.values(), key=lambda a: a["posicion_led"]),
        }
