"""PUT /categorias/{categoria_id} - cambia el nombre o la descripcion de una categoria."""

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
    categoria_id = validacion.parametro_ruta(event, "categoria_id")
    cuerpo = _obtener_servicio().actualizar(categoria_id, validacion.cuerpo_json(event))
    return respuesta(200, cuerpo)
