"""DELETE /objetos/{object_id} - elimina un objeto que ya no tiene existencias.

El historial de movimientos y busquedas no se borra: es la auditoria del inventario.
"""

from localizador import autorizacion, validacion
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
    autorizacion.exigir_administrador(event)
    object_id = validacion.parametro_ruta(event, "object_id")
    return respuesta(200, _obtener_servicio().eliminar(object_id))
