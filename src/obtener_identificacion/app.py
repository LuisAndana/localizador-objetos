"""GET /identificaciones/{identificacion_id} - estado y propuesta de una identificacion."""

from localizador import autorizacion, validacion
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioIdentificacion
from localizador.vision_aws import RepositorioIdentificaciones

_servicio: ServicioIdentificacion | None = None


def _obtener_servicio() -> ServicioIdentificacion:
    global _servicio
    if _servicio is None:
        _servicio = ServicioIdentificacion(RepositorioIdentificaciones())
    return _servicio


@handler_api
def lambda_handler(event, context):
    identificacion_id = validacion.parametro_ruta(event, "identificacion_id")
    cuerpo = _obtener_servicio().obtener(identificacion_id, autorizacion.usuario(event))
    return respuesta(200, cuerpo)
