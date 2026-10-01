"""Lectura y validacion de la configuracion desde variables de entorno.

Cada accesor es perezoso y cacheado: una Lambda solo falla por una variable
que realmente necesita, y solo la primera vez (reutilizada en warm start).
"""

import os
import re
from functools import lru_cache

REGEX_ENDPOINT_IOT = re.compile(r"^[a-z0-9][a-z0-9.\-]{4,254}$")


class ConfiguracionInvalida(RuntimeError):
    """La funcion no puede arrancar porque falta configuracion o es invalida."""


def _requerida(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ConfiguracionInvalida(
            f"Falta la variable de entorno obligatoria: {nombre}"
        )
    return valor


def _entera(nombre: str, defecto: int, minimo: int, maximo: int) -> int:
    bruto = os.environ.get(nombre, "").strip()
    if not bruto:
        return defecto
    try:
        valor = int(bruto)
    except ValueError as exc:
        raise ConfiguracionInvalida(f"{nombre} debe ser un entero.") from exc
    if not minimo <= valor <= maximo:
        raise ConfiguracionInvalida(
            f"{nombre} debe estar entre {minimo} y {maximo}."
        )
    return valor


def _bandera(nombre: str, defecto: bool = False) -> bool:
    bruto = os.environ.get(nombre, "").strip().lower()
    if not bruto:
        return defecto
    return bruto in ("1", "true", "yes", "si", "on")


@lru_cache(maxsize=1)
def tabla_objetos() -> str:
    return _requerida("TABLA_OBJETOS")


@lru_cache(maxsize=1)
def tabla_categorias() -> str:
    return _requerida("TABLA_CATEGORIAS")


@lru_cache(maxsize=1)
def tabla_movimientos() -> str:
    return _requerida("TABLA_MOVIMIENTOS")


@lru_cache(maxsize=1)
def tabla_busquedas() -> str:
    return _requerida("TABLA_BUSQUEDAS")


@lru_cache(maxsize=1)
def tabla_identificaciones() -> str:
    return _requerida("TABLA_IDENTIFICACIONES")


@lru_cache(maxsize=1)
def bucket_fotos() -> str:
    return _requerida("BUCKET_FOTOS")


@lru_cache(maxsize=1)
def indice_busquedas_objeto() -> str:
    return os.environ.get("INDICE_BUSQUEDAS_OBJETO", "").strip() or "objeto-index"


@lru_cache(maxsize=1)
def indice_categoria() -> str:
    return os.environ.get("INDICE_CATEGORIA", "").strip() or "categoria-index"


@lru_cache(maxsize=1)
def endpoint_iot() -> str:
    valor = _requerida("IOT_ENDPOINT").lower()
    valor = valor.removeprefix("https://").removeprefix("http://").rstrip("/")
    if not REGEX_ENDPOINT_IOT.match(valor):
        raise ConfiguracionInvalida(
            "IOT_ENDPOINT no parece un host valido de AWS IoT Data-ATS."
        )
    return valor


@lru_cache(maxsize=1)
def autenticacion_activa() -> bool:
    """En AWS la plantilla la activa: API Gateway valida el token de Cognito y
    las Lambdas leen de ahi el grupo del usuario. El modo local no tiene usuarios."""
    return _bandera("AUTENTICACION_ACTIVA", defecto=False)


@lru_cache(maxsize=1)
def origen_cors() -> str:
    return os.environ.get("CORS_ALLOW_ORIGIN", "").strip() or "*"


@lru_cache(maxsize=1)
def endpoint_dynamodb() -> str | None:
    """Solo para DynamoDB Local. En AWS se deja vacio y boto3 resuelve solo."""
    return os.environ.get("DYNAMODB_ENDPOINT_URL", "").strip() or None


@lru_cache(maxsize=1)
def iot_simulado() -> bool:
    """Si esta activo, la publicacion MQTT se registra en log y no sale a AWS."""
    return _bandera("IOT_MODO_SIMULACION", defecto=False)


@lru_cache(maxsize=1)
def duracion_led_defecto() -> int:
    return _entera("DURACION_LED_DEFECTO", defecto=30, minimo=1, maximo=300)


@lru_cache(maxsize=1)
def duracion_led_maxima() -> int:
    return _entera("DURACION_LED_MAXIMA", defecto=300, minimo=1, maximo=3600)


@lru_cache(maxsize=1)
def limite_pagina_defecto() -> int:
    return _entera("LIMITE_PAGINA_DEFECTO", defecto=50, minimo=1, maximo=1000)


@lru_cache(maxsize=1)
def limite_pagina_maximo() -> int:
    return _entera("LIMITE_PAGINA_MAXIMO", defecto=200, minimo=1, maximo=1000)


@lru_cache(maxsize=1)
def nivel_log() -> str:
    return (os.environ.get("LOG_LEVEL", "").strip() or "INFO").upper()
