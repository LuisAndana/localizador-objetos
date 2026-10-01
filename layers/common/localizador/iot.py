"""Publicacion MQTT hacia AWS IoT Core (capa fisica: nodos ESP32 + WS2812B)."""

import json
import logging

import boto3
from botocore.config import Config as ConfigBoto

from . import config
from .modelos import PLANTILLA_TOPIC, OrdenLed
from .validacion import identificador

logger = logging.getLogger(__name__)

QOS_AL_MENOS_UNA_VEZ = 1

_CONFIG_BOTO = ConfigBoto(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=2,
    read_timeout=5,
)

_cliente = None


def _cliente_iot():
    global _cliente
    if _cliente is None:
        _cliente = boto3.client(
            "iot-data",
            endpoint_url=f"https://{config.endpoint_iot()}",
            config=_CONFIG_BOTO,
        )
    return _cliente


class PublicadorLed:
    """Traduce una orden de dominio a un mensaje MQTT en el topic del almacen."""

    def __init__(self, cliente=None):
        self._cliente = cliente

    def publicar(self, almacen_id: str, orden: OrdenLed) -> str:
        # Revalidado aqui aunque ya venga limpio: `almacen_id` se interpola en
        # el topic y un '/', '#' o '+' permitiria publicar en topics ajenos.
        almacen_id = identificador(almacen_id, "almacen_id")
        topic = PLANTILLA_TOPIC.format(almacen_id=almacen_id)
        payload = json.dumps(orden.a_payload(), ensure_ascii=False)

        if config.iot_simulado():
            logger.info(
                "[SIMULACION] MQTT no enviado. topic=%s payload=%s", topic, payload
            )
            return topic

        cliente = self._cliente or _cliente_iot()
        cliente.publish(topic=topic, qos=QOS_AL_MENOS_UNA_VEZ, payload=payload)
        logger.info(
            "Orden LED publicada. topic=%s object_id=%s led=%s duracion=%ss",
            topic,
            orden.object_id,
            orden.posicion_led,
            orden.duracion_segundos,
        )
        return topic
