"""POST /busquedas - registra una medicion manual de referencia.

Es el metodo anterior cronometrado a mano: sin estas mediciones no hay contra
que comparar el tiempo del sistema, y el indicador del acta no se puede calcular.
"""

from localizador import validacion
from localizador.repositorios import RepositorioBusquedas
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioBusquedas

_servicio: ServicioBusquedas | None = None


def _obtener_servicio() -> ServicioBusquedas:
    global _servicio
    if _servicio is None:
        _servicio = ServicioBusquedas(RepositorioBusquedas())
    return _servicio


@handler_api
def lambda_handler(event, context):
    cuerpo = _obtener_servicio().registrar_control(validacion.cuerpo_json(event))
    return respuesta(201, cuerpo)
