"""GET /almacenes/{almacen_id}/plano - mapa 2D del almacen.

Devuelve pasillos, anaqueles y niveles con los objetos de cada uno, para que la
app dibuje el plano y resalte donde esta el objeto buscado.
"""

from localizador import validacion
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
    almacen_id = validacion.parametro_ruta(event, "almacen_id")
    return respuesta(200, _obtener_servicio().obtener(almacen_id))
