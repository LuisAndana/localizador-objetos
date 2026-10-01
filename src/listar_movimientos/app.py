"""GET /movimientos?object_id={id} - historial de entradas y salidas de un objeto."""

from localizador import paginacion, validacion
from localizador.repositorios import RepositorioMovimientos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioMovimientos

_servicio: ServicioMovimientos | None = None


def _obtener_servicio() -> ServicioMovimientos:
    global _servicio
    if _servicio is None:
        _servicio = ServicioMovimientos(RepositorioMovimientos())
    return _servicio


@handler_api
def lambda_handler(event, context):
    cuerpo = _obtener_servicio().listar(
        validacion.parametro_query_obligatorio(event, "object_id"),
        validacion.limite_pagina(event),
        paginacion.decodificar_cursor(validacion.parametro_query(event, "cursor")),
    )
    return respuesta(200, cuerpo)
