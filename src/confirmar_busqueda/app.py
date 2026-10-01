"""POST /busquedas/{busqueda_id}/confirmar - detiene el cronometro de una busqueda."""

from localizador import validacion
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
    busqueda_id = validacion.parametro_ruta(event, "busqueda_id")
    return respuesta(200, _obtener_servicio().confirmar(busqueda_id))
