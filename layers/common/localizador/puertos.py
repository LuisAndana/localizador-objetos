"""Contratos que el dominio espera de la infraestructura.

En AWS los cumplen DynamoDB (`repositorios.py`) e IoT Core (`iot.py`); en local,
SQLite y el simulador de nodos (`servidor_local/`). Los servicios solo conocen
estos contratos, por eso la misma lógica corre en los dos entornos.
"""

from typing import Protocol

from .modelos import OrdenLed

Pagina = tuple[list[dict], dict | None]


class PuertoObjetos(Protocol):
    def obtener(self, object_id: str) -> dict: ...

    def crear(self, datos: dict) -> dict: ...

    def actualizar(self, object_id: str, cambios: dict) -> dict: ...

    def eliminar(self, object_id: str) -> dict:
        """Borra el objeto solo si no le quedan existencias. Devuelve lo borrado."""
        ...

    def buscar(
        self, termino: str, categoria: str | None, limite: int, cursor: dict | None = None
    ) -> Pagina:
        """Objetos cuyo nombre normalizado (o id) contiene `termino`."""
        ...

    def hay_en_categoria(self, categoria: str) -> bool: ...

    def listar_por_categoria(
        self, categoria: str, limite: int, cursor: dict | None = None
    ) -> Pagina: ...

    def listar_todos(self, limite: int, cursor: dict | None = None) -> Pagina: ...

    # El mapa 2D necesita el almacen completo, no una pagina: se dibuja entero.
    def listar_por_almacen(self, almacen_id: str) -> list[dict]: ...

    def resumen_almacenes(self) -> list[dict]: ...


class PuertoMovimientos(Protocol):
    def registrar(self, movimiento: dict, delta: int) -> dict:
        """Escribe el movimiento y ajusta la cantidad del objeto en una sola
        operacion atomica. Devuelve el objeto ya actualizado."""
        ...

    def listar_por_objeto(
        self, object_id: str, limite: int, cursor: dict | None = None
    ) -> Pagina: ...


class PuertoCategorias(Protocol):
    def listar(self, limite: int, cursor: dict | None = None) -> Pagina: ...

    def existe(self, categoria_id: str) -> bool: ...

    def crear(self, categoria: dict) -> dict: ...

    def actualizar(self, categoria_id: str, cambios: dict) -> dict: ...

    def eliminar(self, categoria_id: str) -> dict: ...


class PuertoBusquedas(Protocol):
    def abrir(self, busqueda: dict) -> dict: ...

    def confirmar(self, busqueda_id: str, cerrada_por: str) -> dict: ...

    def cerrar_por_objeto(self, object_id: str, cerrada_por: str) -> dict | None:
        """Cierra la busqueda abierta mas reciente del objeto, si la hay."""
        ...

    def registrar_control(self, busqueda: dict) -> dict: ...

    def listar(self, limite: int) -> list[dict]: ...


class PuertoPublicador(Protocol):
    def publicar(self, almacen_id: str, orden: OrdenLed) -> str: ...


class PuertoIdentificaciones(Protocol):
    """Las solicitudes de identificacion por foto y su resultado."""

    def crear(self, identificacion: dict) -> dict: ...

    def obtener(self, identificacion_id: str) -> dict: ...

    def completar(self, identificacion_id: str, propuesta: dict) -> None: ...

    def fallar(self, identificacion_id: str, motivo: str) -> None: ...


class PuertoFotos(Protocol):
    def url_subida(self, clave: str) -> dict:
        """URL prefirmada para que el navegador suba la foto directo al almacen."""
        ...


class PuertoReconocimiento(Protocol):
    def analizar(self, clave: str) -> tuple[list[dict], list[dict]]:
        """(etiquetas, detecciones de texto) de la foto guardada en `clave`."""
        ...
