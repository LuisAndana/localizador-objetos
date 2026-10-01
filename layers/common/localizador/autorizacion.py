"""Quien puede hacer que.

API Gateway ya comprobo el token de Cognito antes de llamar a la Lambda: si la
peticion llega aqui, el usuario inicio sesion. Lo que falta decidir es si su
grupo le permite la operacion. Registrar, editar, mover material y localizar lo
puede hacer cualquier usuario; borrar objetos y gestionar categorias, solo un
administrador, porque son cambios que no se deshacen.
"""

import re

from . import config
from .errores import ErrorProhibido

GRUPO_ADMINISTRADORES = "administradores"


def grupos(event: dict) -> set[str]:
    """Grupos de Cognito del usuario, tal como los entrega el autorizador.

    En una API REST el claim `cognito:groups` llega como texto: "admin" si hay
    un grupo, o "[admin ops]" / "admin,ops" si hay varios, segun la version.
    """
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("claims") or {}
    bruto = claims.get("cognito:groups") or ""
    if isinstance(bruto, list):
        return {str(g) for g in bruto if g}
    return {g for g in re.split(r"[\[\],\s]+", str(bruto)) if g}


def usuario(event: dict) -> str | None:
    """Id estable del usuario (`sub` de Cognito), o None sin autenticacion."""
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("claims") or {}
    return claims.get("sub") or None


def exigir_administrador(event: dict) -> None:
    if not config.autenticacion_activa():
        return
    if GRUPO_ADMINISTRADORES not in grupos(event):
        raise ErrorProhibido(
            "Esta operacion solo la puede hacer un administrador."
        )
