"""GET /objetos?categoria={categoria}&q={texto} - lista o busca objetos por nombre."""

from localizador import paginacion, validacion
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
    cuerpo = _obtener_servicio().listar(
        validacion.parametro_query(event, "categoria"),
        validacion.limite_pagina(event),
        paginacion.decodificar_cursor(validacion.parametro_query(event, "cursor")),
        validacion.parametro_query(event, "q"),
    )
    return respuesta(200, cuerpo)
