"""POST /objetos - registra un objeto nuevo."""

from localizador import validacion
from localizador.repositorios import RepositorioCategorias, RepositorioObjetos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioObjetos

_servicio: ServicioObjetos | None = None


def _obtener_servicio() -> ServicioObjetos:
    global _servicio
    if _servicio is None:
        # Las categorias solo se consultan para rechazar una que no exista.
        _servicio = ServicioObjetos(RepositorioObjetos(), RepositorioCategorias())
    return _servicio


@handler_api
def lambda_handler(event, context):
    return respuesta(201, _obtener_servicio().crear(validacion.cuerpo_json(event)))
