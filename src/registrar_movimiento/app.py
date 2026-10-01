"""POST /movimientos - registra una entrada o salida y ajusta la cantidad."""

from localizador import validacion
from localizador.repositorios import RepositorioBusquedas, RepositorioMovimientos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioMovimientos

_servicio: ServicioMovimientos | None = None


def _obtener_servicio() -> ServicioMovimientos:
    global _servicio
    if _servicio is None:
        # Una salida cierra la busqueda abierta del objeto: de ahi sale el tiempo medido.
        _servicio = ServicioMovimientos(RepositorioMovimientos(), RepositorioBusquedas())
    return _servicio


@handler_api
def lambda_handler(event, context):
    cuerpo = _obtener_servicio().registrar(validacion.cuerpo_json(event))
    return respuesta(201, cuerpo)
