"""POST /identificaciones - pide una URL para subir la foto de un objeto a identificar.

La foto va del navegador directo a S3 con la URL prefirmada; al llegar, el evento
de S3 dispara `identificar_objeto`. La app consulta el resultado con
GET /identificaciones/{identificacion_id}.
"""

from localizador import autorizacion
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioIdentificacion
from localizador.vision_aws import AlmacenFotosS3, RepositorioIdentificaciones

_servicio: ServicioIdentificacion | None = None


def _obtener_servicio() -> ServicioIdentificacion:
    global _servicio
    if _servicio is None:
        _servicio = ServicioIdentificacion(RepositorioIdentificaciones(), fotos=AlmacenFotosS3())
    return _servicio


@handler_api
def lambda_handler(event, context):
    return respuesta(201, _obtener_servicio().solicitar(autorizacion.usuario(event)))
