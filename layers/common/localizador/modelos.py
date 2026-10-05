"""Modelo de dominio. Independiente de DynamoDB, API Gateway e IoT Core."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

# Contrato con el firmware del ESP32: cada nodo se suscribe al topic de su almacén.
PLANTILLA_TOPIC = "almacen/{almacen_id}/led"


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ahora_iso_preciso() -> str:
    """Marca de tiempo con microsegundos.

    El historial de movimientos se ordena por esta cadena: con precision de
    segundos, dos movimientos del mismo segundo empatan y el orden lo decidiria
    el UUID, que es aleatorio. Con microsegundos el orden es el real.
    """
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class Ubicacion:
    almacen_id: str
    pasillo: str
    anaquel: str
    nivel: str
    posicion_led: int
    columna: str = "A"

    def descripcion(self) -> str:
        return (
            f"Almacen {self.almacen_id}, pasillo {self.pasillo}, "
            f"anaquel {self.anaquel}, nivel {self.nivel}, columna {self.columna}"
        )


@dataclass(frozen=True, slots=True)
class Objeto:
    object_id: str
    nombre: str
    categoria: str
    ubicacion: Ubicacion
    color_indicador: str
    ultima_actualizacion: str = field(default_factory=ahora_iso)

    @classmethod
    def desde_item(cls, item: dict) -> "Objeto":
        return cls(
            object_id=item["object_id"],
            nombre=item["nombre"],
            categoria=item["categoria"],
            ubicacion=Ubicacion(
                almacen_id=item["almacen_id"],
                pasillo=item["pasillo"],
                anaquel=item["anaquel"],
                nivel=item["nivel"],
                posicion_led=int(item["posicion_led"]),
                columna=item.get("columna") or "A",
            ),
            color_indicador=item["color_indicador"],
            ultima_actualizacion=item.get("ultima_actualizacion", ""),
        )

    def a_item(self) -> dict:
        return {
            "object_id": self.object_id,
            "nombre": self.nombre,
            "categoria": self.categoria,
            "almacen_id": self.ubicacion.almacen_id,
            "pasillo": self.ubicacion.pasillo,
            "anaquel": self.ubicacion.anaquel,
            "nivel": self.ubicacion.nivel,
            "columna": self.ubicacion.columna,
            "posicion_led": self.ubicacion.posicion_led,
            "color_indicador": self.color_indicador,
            "ultima_actualizacion": self.ultima_actualizacion,
        }


TIPOS_MOVIMIENTO = ("entrada", "salida")
ORIGENES_MOVIMIENTO = ("app", "asistente", "sensor")


@dataclass(frozen=True, slots=True)
class Movimiento:
    """Entrada o salida de material: el historial que ajusta la cantidad del objeto."""

    movimiento_id: str
    object_id: str
    tipo: str
    cantidad: int
    origen: str = "app"
    motivo: str = ""
    referencia: str = ""
    registrado_en: str = field(default_factory=ahora_iso_preciso)

    @property
    def delta(self) -> int:
        """Cuanto cambia la cantidad del objeto: positivo entra, negativo sale."""
        return self.cantidad if self.tipo == "entrada" else -self.cantidad

    @property
    def clave_orden(self) -> str:
        """Clave de ordenamiento del historial.

        Lleva el id ademas de la marca de tiempo porque dos movimientos del mismo
        objeto pueden caer en el mismo segundo y uno sobrescribiria al otro.
        """
        return f"{self.registrado_en}#{self.movimiento_id}"

    @classmethod
    def desde_item(cls, item: dict) -> "Movimiento":
        return cls(
            movimiento_id=item["movimiento_id"],
            object_id=item["object_id"],
            tipo=item["tipo"],
            cantidad=int(item["cantidad"]),
            origen=item.get("origen", "app"),
            motivo=item.get("motivo", ""),
            referencia=item.get("referencia", ""),
            registrado_en=item.get("registrado_en", ""),
        )

    def a_item(self) -> dict:
        return {
            "object_id": self.object_id,
            "clave_orden": self.clave_orden,
            "movimiento_id": self.movimiento_id,
            "tipo": self.tipo,
            "cantidad": self.cantidad,
            "origen": self.origen,
            "motivo": self.motivo,
            "referencia": self.referencia,
            "registrado_en": self.registrado_en,
        }


MODOS_BUSQUEDA = ("sistema", "control")
CIERRES_BUSQUEDA = ("salida", "app")


@dataclass(frozen=True, slots=True)
class Busqueda:
    """Una localizacion cronometrada, para medir el indicador de tiempo del acta.

    `sistema` es una busqueda hecha con el localizador; `control` es una medicion
    manual del metodo anterior, que sirve de referencia para comparar.
    """

    busqueda_id: str
    object_id: str
    modo: str = "sistema"
    iniciada_en: str = field(default_factory=ahora_iso_preciso)
    confirmada_en: str = ""
    duracion_ms: int = 0
    cerrada_por: str = ""

    @property
    def abierta(self) -> bool:
        return not self.confirmada_en

    @classmethod
    def desde_item(cls, item: dict) -> "Busqueda":
        return cls(
            busqueda_id=item["busqueda_id"],
            object_id=item["object_id"],
            modo=item.get("modo", "sistema"),
            iniciada_en=item.get("iniciada_en", ""),
            confirmada_en=item.get("confirmada_en", ""),
            duracion_ms=int(item.get("duracion_ms", 0)),
            cerrada_por=item.get("cerrada_por", ""),
        )

    def a_item(self) -> dict:
        return {
            "busqueda_id": self.busqueda_id,
            "object_id": self.object_id,
            "modo": self.modo,
            "iniciada_en": self.iniciada_en,
            "confirmada_en": self.confirmada_en,
            "duracion_ms": self.duracion_ms,
            "cerrada_por": self.cerrada_por,
        }


@dataclass(frozen=True, slots=True)
class OrdenLed:
    """Lo que se publica por MQTT y consume el nodo ESP32."""

    posicion_led: int
    color_indicador: str
    duracion_segundos: int
    object_id: str
    emitido_en: str = field(default_factory=ahora_iso)

    def a_payload(self) -> dict:
        return {
            "posicion_led": self.posicion_led,
            "color_indicador": self.color_indicador,
            "duracion_segundos": self.duracion_segundos,
            "object_id": self.object_id,
            "emitido_en": self.emitido_en,
        }
