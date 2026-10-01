"""GET /almacenes - almacenes con objetos registrados, para elegir en el mapa."""

from localizador.repositorios import RepositorioObjetos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioPlano

_servicio: ServicioPlano | None = None


def _obtener_servicio() -> ServicioPlano:
    global _servicio
    if _servicio is None:
        _servicio = ServicioPlano(RepositorioObjetos())
    return _servicio


@handler_api
def lambda_handler(event, context):
    return respuesta(200, _obtener_servicio().almacenes())
