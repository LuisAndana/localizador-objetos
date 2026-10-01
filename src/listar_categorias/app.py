"""GET /categorias - lista el catalogo de categorias."""

from localizador import paginacion, validacion
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
    cuerpo = _obtener_servicio().listar(
        validacion.limite_pagina(event),
        paginacion.decodificar_cursor(validacion.parametro_query(event, "cursor")),
    )
    return respuesta(200, cuerpo)
