"""DELETE /categorias/{categoria_id} - elimina una categoria sin objetos."""

from localizador import autorizacion, validacion
from localizador.repositorios import RepositorioCategorias, RepositorioObjetos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioCategorias

_servicio: ServicioCategorias | None = None


def _obtener_servicio() -> ServicioCategorias:
    global _servicio
    if _servicio is None:
        # Los objetos se consultan para no dejar ninguno con la categoria borrada.
        _servicio = ServicioCategorias(RepositorioCategorias(), RepositorioObjetos())
    return _servicio


@handler_api
def lambda_handler(event, context):
    autorizacion.exigir_administrador(event)
    categoria_id = validacion.parametro_ruta(event, "categoria_id")
    return respuesta(200, _obtener_servicio().eliminar(categoria_id))
