"""Cognito PreSignUp: solo se registran correos de los dominios permitidos.

Cognito la llama antes de crear cada cuenta. Si el correo no pertenece a un
dominio de DOMINIOS_PERMITIDOS, se rechaza: no se crea la cuenta ni se envia
ningun codigo. Sin dominios configurados, nadie puede registrarse.
"""

import os
import re

_CORREO = re.compile(r"^[a-z0-9._%+-]{1,64}@([a-z0-9-]+\.)+[a-z]{2,}$")


def _dominios_permitidos() -> set[str]:
    crudo = os.environ.get("DOMINIOS_PERMITIDOS", "")
    return {d.strip().lower() for d in crudo.split(",") if d.strip()}


def correo_permitido(correo: str, dominios: set[str]) -> bool:
    correo = correo.strip().lower()
    if not _CORREO.fullmatch(correo):
        return False
    return correo.rsplit("@", 1)[1] in dominios


def lambda_handler(event, context):
    atributos = (event.get("request") or {}).get("userAttributes") or {}
    if not correo_permitido(str(atributos.get("email", "")), _dominios_permitidos()):
        # Mensaje generico: no revela que dominios estan permitidos.
        raise Exception("Registro no permitido para este correo.")
    # Cuenta sin confirmar: el correo se verifica con el codigo que Cognito envia.
    event["response"]["autoConfirmUser"] = False
    event["response"]["autoVerifyEmail"] = False
    return event
