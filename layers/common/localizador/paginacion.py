"""Paginacion por cursor (keyset) sobre DynamoDB.

Se expone el `LastEvaluatedKey` al cliente como un cursor opaco en base64url.
Es preferible a `offset` porque no se degrada con el tamano de la tabla y no
reprocesa las paginas anteriores.
"""

import base64
import binascii
import json
from typing import Any

from .errores import ErrorValidacion

LONGITUD_MAXIMA_CURSOR = 2048
TIPOS_ESCALARES = (str, int, float, bool)


def codificar_cursor(clave: dict | None) -> str | None:
    if not clave:
        return None
    crudo = json.dumps(clave, separators=(",", ":"), default=str).encode("utf-8")
    return base64.urlsafe_b64encode(crudo).decode("ascii")


def decodificar_cursor(cursor: str | None) -> dict | None:
    if not cursor:
        return None
    if len(cursor) > LONGITUD_MAXIMA_CURSOR:
        raise ErrorValidacion("El cursor es invalido.")
    try:
        crudo = base64.urlsafe_b64decode(cursor.encode("ascii"))
        clave = json.loads(crudo)
    except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
        raise ErrorValidacion("El cursor es invalido.") from exc

    if not isinstance(clave, dict) or not clave:
        raise ErrorValidacion("El cursor es invalido.")
    if len(clave) > 4 or not all(
        isinstance(k, str) and isinstance(v, TIPOS_ESCALARES) for k, v in clave.items()
    ):
        raise ErrorValidacion("El cursor es invalido.")
    return clave


def pagina(elementos: list[dict], ultima_clave: dict | None) -> dict[str, Any]:
    return {
        "elementos": elementos,
        "total_en_pagina": len(elementos),
        "siguiente_cursor": codificar_cursor(ultima_clave),
    }
