"""POST /objetos/{object_id}/localizar - enciende el LED fisico del objeto.

Busca el objeto en DynamoDB y publica una orden MQTT en `almacen/{id}/led`
para que el nodo ESP32 correspondiente ilumine el LED de esa posicion.
"""

from localizador import validacion
from localizador.iot import PublicadorLed
from localizador.repositorios import RepositorioBusquedas, RepositorioObjetos
from localizador.respuestas import handler_api, respuesta
from localizador.servicios import ServicioLocalizacion

_servicio: ServicioLocalizacion | None = None


def _obtener_servicio() -> ServicioLocalizacion:
    global _servicio
    if _servicio is None:
        # La busqueda abierta aqui es la que arranca el cronometro del indicador.
        _servicio = ServicioLocalizacion(
            RepositorioObjetos(), PublicadorLed(), RepositorioBusquedas()
        )
    return _servicio


@handler_api
def lambda_handler(event, context):
    object_id = validacion.parametro_ruta(event, "object_id")
    duracion = validacion.duracion_localizacion(
        validacion.cuerpo_json(event, obligatorio=False)
    )
    return respuesta(202, _obtener_servicio().localizar(object_id, duracion))
