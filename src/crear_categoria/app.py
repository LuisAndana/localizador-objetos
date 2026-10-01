"""POST /categorias - da de alta una categoria."""

from localizador import autorizacion, validacion
from localizador.repositorios import RepositorioCategorias
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioCategorias

_servicio: ServicioCategorias | None = None


def _obtener_servicio() -> ServicioCategorias:
    global _servicio
    if _servicio is None:
        _servicio = ServicioCategorias(RepositorioCategorias())
    return _servicio


@handler_api
def lambda_handler(event, context):
    autorizacion.exigir_administrador(event)
    return respuesta(201, _obtener_servicio().crear(validacion.cuerpo_json(event)))
