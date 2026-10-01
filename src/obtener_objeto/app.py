"""GET /objetos/{object_id} - detalle de un objeto."""

from localizador import validacion
from localizador.repositorios import RepositorioObjetos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioObjetos

_servicio: ServicioObjetos | None = None


def _obtener_servicio() -> ServicioObjetos:
    global _servicio
    if _servicio is None:
        _servicio = ServicioObjetos(RepositorioObjetos())
    return _servicio


@handler_api
def lambda_handler(event, context):
    object_id = validacion.parametro_ruta(event, "object_id")
    return respuesta(200, _obtener_servicio().obtener(object_id))
