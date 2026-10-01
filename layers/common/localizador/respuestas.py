"""Serializacion HTTP, CORS y el decorador que envuelve a cada handler."""

import functools
import json
import logging
from decimal import Decimal
from typing import Any, Callable

from botocore.exceptions import BotoCoreError, ClientError

from . import config
from .config import ConfiguracionInvalida
from .errores import ErrorAplicacion

logger = logging.getLogger()

ERRORES_DYNAMO_REINTENTABLES = {
    "ProvisionedThroughputExceededException",
    "ThrottlingException",
    "RequestLimitExceeded",
    "InternalServerError",
    "ServiceUnavailable",
}


def configurar_logging() -> None:
    try:
        nivel = getattr(logging, config.nivel_log(), logging.INFO)
    except ConfiguracionInvalida:
        nivel = logging.INFO
    logging.getLogger().setLevel(nivel)


class CodificadorJSON(json.JSONEncoder):
    """DynamoDB devuelve Decimal; el JSON estandar no sabe serializarlo."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        return super().default(o)


def cabeceras_cors() -> dict[str, str]:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": config.origen_cors(),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }


def respuesta(estado: int, cuerpo: Any) -> dict:
    return {
        "statusCode": estado,
        "headers": cabeceras_cors(),
        "body": json.dumps(cuerpo, cls=CodificadorJSON, ensure_ascii=False),
    }


def respuesta_error(
    estado: int, codigo: str, mensaje: str, detalles: dict | None = None
) -> dict:
    cuerpo: dict[str, Any] = {"error": codigo, "mensaje": mensaje}
    if detalles:
        cuerpo["detalles"] = detalles
    return respuesta(estado, cuerpo)


def handler_api(funcion: Callable[[dict, Any], dict]) -> Callable[[dict, Any], dict]:
    """Traduce excepciones a respuestas HTTP y evita filtrar detalles internos.

    Solo los `ErrorAplicacion` llevan su mensaje al cliente. Todo lo demas se
    registra completo en CloudWatch y sale como 500 generico.
    """

    @functools.wraps(funcion)
    def envoltura(event: dict, context: Any) -> dict:
        configurar_logging()
        peticion_id = getattr(context, "aws_request_id", "local")
        try:
            return funcion(event, context)

        except ErrorAplicacion as exc:
            logger.warning(
                "Error de aplicacion (%s): %s", exc.codigo, exc.mensaje,
                extra={"request_id": peticion_id},
            )
            return respuesta_error(exc.estado_http, exc.codigo, exc.mensaje, exc.detalles)

        except ConfiguracionInvalida:
            logger.exception("Configuracion invalida en la funcion")
            return respuesta_error(
                500, "error_interno", "Error interno del servidor."
            )

        except ClientError as exc:
            codigo_aws = exc.response.get("Error", {}).get("Code", "Desconocido")
            logger.exception("Fallo de servicio AWS: %s", codigo_aws)
            if codigo_aws in ERRORES_DYNAMO_REINTENTABLES:
                return respuesta_error(
                    503,
                    "dependencia_no_disponible",
                    "El servicio esta saturado. Reintenta en unos segundos.",
                )
            return respuesta_error(500, "error_interno", "Error interno del servidor.")

        except BotoCoreError:
            logger.exception("Fallo de conectividad con AWS")
            return respuesta_error(
                503,
                "dependencia_no_disponible",
                "No se pudo contactar un servicio dependiente.",
            )

        except Exception:  # noqa: BLE001 - red de seguridad final
            logger.exception("Error no controlado")
            return respuesta_error(500, "error_interno", "Error interno del servidor.")

    return envoltura
