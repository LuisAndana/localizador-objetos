"""GET /metricas/localizacion - indicador de tiempo: manual contra sistema."""

from localizador.repositorios import RepositorioBusquedas
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioBusquedas

_servicio: ServicioBusquedas | None = None


def _obtener_servicio() -> ServicioBusquedas:
    global _servicio
    if _servicio is None:
        _servicio = ServicioBusquedas(RepositorioBusquedas())
    return _servicio


@handler_api
def lambda_handler(event, context):
    return respuesta(200, _obtener_servicio().resumen())
