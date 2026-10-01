"""Evento de S3: llego una foto. Rekognition la analiza y se guarda la propuesta.

No es un endpoint HTTP: la dispara S3 al crear un objeto en fotos/*.jpg.
La IA solo propone; la persona confirma en el formulario de registro.
"""

import logging
from urllib.parse import unquote_plus

from localizador.repositorios import RepositorioCategorias
from localizador.respuestas import configurar_logging
from localizador.servicios import ServicioIdentificacion
from localizador.vision_aws import ReconocimientoRekognition, RepositorioIdentificaciones

logger = logging.getLogger()

_servicio: ServicioIdentificacion | None = None


def _obtener_servicio() -> ServicioIdentificacion:
    global _servicio
    if _servicio is None:
        _servicio = ServicioIdentificacion(
            RepositorioIdentificaciones(),
            reconocimiento=ReconocimientoRekognition(),
            categorias=RepositorioCategorias(),
        )
    return _servicio


def lambda_handler(event, context):
    configurar_logging()
    procesadas = []
    for registro in event.get("Records", []):
        # S3 manda la clave codificada como en una URL ("+" por espacio).
        clave = unquote_plus(registro.get("s3", {}).get("object", {}).get("key", ""))
        identificacion_id = _obtener_servicio().procesar(clave)
        if identificacion_id is None:
            logger.warning("Foto ignorada: la clave no la genero la API (%s)", clave[:120])
            continue
        logger.info("Identificacion %s lista", identificacion_id)
        procesadas.append(identificacion_id)
    return {"procesadas": procesadas}
