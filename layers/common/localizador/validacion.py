"""Validacion y normalizacion de toda entrada que viene del exterior.

Nada que provenga del cliente llega a DynamoDB o a un topic MQTT sin pasar
por aqui. `almacen_id` y `object_id` son especialmente estrictos porque se
interpolan en el nombre del topic: un valor con `/`, `#` o `+` permitiria
publicar en topics ajenos (inyeccion de topic MQTT).
"""

import json
import re
import unicodedata
from typing import Any

from . import config
from .errores import ErrorValidacion
from .modelos import ORIGENES_MOVIMIENTO, TIPOS_MOVIMIENTO

REGEX_IDENTIFICADOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")
REGEX_COLOR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Columna del anaquel: una letra o un numero corto, como esta rotulado ("A", "B", "12").
REGEX_COLUMNA = re.compile(r"^[A-Za-z0-9]{1,3}$")
COLUMNA_POR_DEFECTO = "A"

LONGITUD_MAXIMA_CUERPO = 16 * 1024
COLOR_POR_DEFECTO = "#00FF00"

CAMPOS_UBICACION = ("almacen_id", "pasillo", "anaquel", "nivel", "posicion_led")
CAMPOS_ACTUALIZABLES = CAMPOS_UBICACION + ("columna", "nombre", "categoria", "color_indicador", "cantidad")

CANTIDAD_MAXIMA = 100_000
CANTIDAD_MAXIMA_MOVIMIENTO = 10_000


def cuerpo_json(event: dict, obligatorio: bool = True) -> dict:
    bruto = event.get("body") or ""
    if event.get("isBase64Encoded"):
        import base64

        try:
            bruto = base64.b64decode(bruto).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ErrorValidacion("El cuerpo no es UTF-8 valido.") from exc

    if not bruto.strip():
        if obligatorio:
            raise ErrorValidacion("Se esperaba un cuerpo JSON.")
        return {}

    if len(bruto) > LONGITUD_MAXIMA_CUERPO:
        raise ErrorValidacion("El cuerpo de la peticion es demasiado grande.")

    try:
        datos = json.loads(bruto)
    except json.JSONDecodeError as exc:
        raise ErrorValidacion("El cuerpo no es JSON valido.") from exc

    if not isinstance(datos, dict):
        raise ErrorValidacion("El cuerpo debe ser un objeto JSON.")
    return datos


def parametro_ruta(event: dict, nombre: str) -> str:
    valor = (event.get("pathParameters") or {}).get(nombre) or ""
    return identificador(valor, nombre)


def parametro_query(event: dict, nombre: str) -> str | None:
    valor = (event.get("queryStringParameters") or {}).get(nombre)
    if valor is None:
        return None
    valor = str(valor).strip()
    return valor or None


def parametro_query_obligatorio(event: dict, nombre: str) -> str:
    valor = parametro_query(event, nombre)
    if valor is None:
        raise ErrorValidacion(f"Falta el parametro '{nombre}' en la consulta.")
    return valor


def identificador(valor: Any, campo: str) -> str:
    if not isinstance(valor, str):
        raise ErrorValidacion(f"'{campo}' debe ser texto.")
    valor = valor.strip()
    if not REGEX_IDENTIFICADOR.match(valor):
        raise ErrorValidacion(
            f"'{campo}' solo admite letras, numeros, guion y guion bajo "
            "(1 a 64 caracteres, empezando por alfanumerico)."
        )
    return valor


def texto(valor: Any, campo: str, maximo: int, minimo: int = 1) -> str:
    if not isinstance(valor, str):
        raise ErrorValidacion(f"'{campo}' debe ser texto.")
    valor = valor.strip()
    if not minimo <= len(valor) <= maximo:
        raise ErrorValidacion(
            f"'{campo}' debe tener entre {minimo} y {maximo} caracteres."
        )
    if any(ord(c) < 32 for c in valor):
        raise ErrorValidacion(f"'{campo}' contiene caracteres de control.")
    return valor


def entero(valor: Any, campo: str, minimo: int, maximo: int) -> int:
    # bool es subclase de int en Python: True pasaria como 1 sin este guardia.
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ErrorValidacion(f"'{campo}' debe ser un numero entero.")
    if not minimo <= valor <= maximo:
        raise ErrorValidacion(f"'{campo}' debe estar entre {minimo} y {maximo}.")
    return valor


def columna(valor: Any) -> str:
    if not isinstance(valor, str) or not REGEX_COLUMNA.match(valor.strip()):
        raise ErrorValidacion("'columna' debe ser una letra o un numero de 1 a 3 caracteres (ej. A, B, 12).")
    return valor.strip().upper()


def color_hex(valor: Any, campo: str = "color_indicador") -> str:
    if not isinstance(valor, str) or not REGEX_COLOR_HEX.match(valor.strip()):
        raise ErrorValidacion(f"'{campo}' debe tener el formato #RRGGBB.")
    return valor.strip().upper()


def _validar_campo(campo: str, valor: Any) -> Any:
    if campo == "nombre":
        return texto(valor, "nombre", maximo=120)
    if campo == "categoria":
        return identificador(valor, "categoria")
    if campo == "almacen_id":
        return identificador(valor, "almacen_id")
    if campo in ("pasillo", "anaquel", "nivel"):
        return texto(valor, campo, maximo=30)
    if campo == "columna":
        return columna(valor)
    if campo == "posicion_led":
        return entero(valor, "posicion_led", minimo=0, maximo=65535)
    if campo == "color_indicador":
        return color_hex(valor)
    if campo == "cantidad":
        return entero(valor, "cantidad", minimo=0, maximo=CANTIDAD_MAXIMA)
    raise ErrorValidacion(f"Campo no reconocido: '{campo}'.")


def objeto_nuevo(datos: dict) -> dict:
    """Valida el cuerpo de POST /objetos. Todo obligatorio salvo el color."""
    obligatorios = ("nombre", "categoria") + CAMPOS_UBICACION
    faltantes = [c for c in obligatorios if c not in datos]
    if faltantes:
        raise ErrorValidacion(
            "Faltan campos obligatorios.", {"campos": sorted(faltantes)}
        )

    limpio = {campo: _validar_campo(campo, datos[campo]) for campo in obligatorios}
    # Opcional para no romper a quien ya registraba sin columna: va a la primera.
    limpio["columna"] = columna(datos["columna"]) if "columna" in datos else COLUMNA_POR_DEFECTO
    limpio["color_indicador"] = (
        color_hex(datos["color_indicador"])
        if "color_indicador" in datos
        else COLOR_POR_DEFECTO
    )
    # Un objeto nace sin existencias: la cantidad la mueven las entradas y salidas.
    limpio["cantidad"] = (
        entero(datos["cantidad"], "cantidad", minimo=0, maximo=CANTIDAD_MAXIMA)
        if "cantidad" in datos
        else 0
    )

    if "object_id" in datos:
        limpio["object_id"] = identificador(datos["object_id"], "object_id")

    return limpio


def movimiento_nuevo(datos: dict) -> dict:
    """Valida el cuerpo de POST /movimientos (una entrada o una salida)."""
    faltantes = [c for c in ("object_id", "tipo", "cantidad") if c not in datos]
    if faltantes:
        raise ErrorValidacion(
            "Faltan campos obligatorios.", {"campos": sorted(faltantes)}
        )

    tipo = datos["tipo"]
    if tipo not in TIPOS_MOVIMIENTO:
        raise ErrorValidacion(
            "'tipo' debe ser 'entrada' o 'salida'.", {"recibido": str(tipo)[:40]}
        )

    origen = datos.get("origen", "app")
    if origen not in ORIGENES_MOVIMIENTO:
        raise ErrorValidacion(
            "'origen' no es valido.", {"permitidos": list(ORIGENES_MOVIMIENTO)}
        )

    limpio = {
        "object_id": identificador(datos["object_id"], "object_id"),
        "tipo": tipo,
        # Minimo 1: un movimiento de cero piezas no mueve inventario y solo
        # ensuciaria el historial.
        "cantidad": entero(
            datos["cantidad"], "cantidad", minimo=1, maximo=CANTIDAD_MAXIMA_MOVIMIENTO
        ),
        "origen": origen,
    }
    for campo, maximo in (("motivo", 120), ("referencia", 60)):
        if datos.get(campo):
            limpio[campo] = texto(datos[campo], campo, maximo=maximo)
    return limpio


def objeto_actualizacion(datos: dict) -> dict:
    """Valida el cuerpo de PUT /objetos/{id}. Actualizacion parcial."""
    desconocidos = set(datos) - set(CAMPOS_ACTUALIZABLES)
    if desconocidos:
        raise ErrorValidacion(
            "El cuerpo contiene campos no permitidos.",
            {"campos": sorted(desconocidos)},
        )
    if not datos:
        raise ErrorValidacion(
            "Indica al menos un campo a actualizar.",
            {"permitidos": list(CAMPOS_ACTUALIZABLES)},
        )
    return {campo: _validar_campo(campo, valor) for campo, valor in datos.items()}


CAMPOS_CATEGORIA_ACTUALIZABLES = ("nombre", "descripcion")


def categoria_nueva(datos: dict) -> dict:
    """Valida el cuerpo de POST /categorias."""
    faltantes = [c for c in ("categoria_id", "nombre") if c not in datos]
    if faltantes:
        raise ErrorValidacion(
            "Faltan campos obligatorios.", {"campos": sorted(faltantes)}
        )
    desconocidos = set(datos) - {"categoria_id", *CAMPOS_CATEGORIA_ACTUALIZABLES}
    if desconocidos:
        raise ErrorValidacion(
            "El cuerpo contiene campos no permitidos.", {"campos": sorted(desconocidos)}
        )
    return {
        "categoria_id": identificador(datos["categoria_id"], "categoria_id"),
        "nombre": texto(datos["nombre"], "nombre", maximo=60),
        "descripcion": texto(datos.get("descripcion", ""), "descripcion", maximo=200, minimo=0),
    }


def categoria_actualizacion(datos: dict) -> dict:
    """Valida el cuerpo de PUT /categorias/{id}. El id no se cambia: lo usan los objetos."""
    desconocidos = set(datos) - set(CAMPOS_CATEGORIA_ACTUALIZABLES)
    if desconocidos:
        raise ErrorValidacion(
            "El cuerpo contiene campos no permitidos.",
            {"campos": sorted(desconocidos)},
        )
    if not datos:
        raise ErrorValidacion(
            "Indica al menos un campo a actualizar.",
            {"permitidos": list(CAMPOS_CATEGORIA_ACTUALIZABLES)},
        )
    limpio = {}
    if "nombre" in datos:
        limpio["nombre"] = texto(datos["nombre"], "nombre", maximo=60)
    if "descripcion" in datos:
        limpio["descripcion"] = texto(datos["descripcion"], "descripcion", maximo=200, minimo=0)
    return limpio


LONGITUD_MINIMA_BUSQUEDA = 2


def normalizar_busqueda(valor: str) -> str:
    """Minusculas y sin acentos: 'Multímetro' y 'multimetro' deben coincidir.

    Se aplica igual al guardar el nombre y al buscarlo, asi que la comparacion
    nunca depende de como lo haya escrito cada quien.
    """
    sin_acentos = unicodedata.normalize("NFKD", valor)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.lower().split())


def termino_busqueda(valor: str | None) -> str | None:
    """Valida el parametro `q` de GET /objetos y lo devuelve ya normalizado."""
    if valor is None:
        return None
    termino = normalizar_busqueda(texto(valor, "q", maximo=60, minimo=0))
    if not termino:
        return None
    if len(termino) < LONGITUD_MINIMA_BUSQUEDA:
        raise ErrorValidacion(
            f"'q' debe tener al menos {LONGITUD_MINIMA_BUSQUEDA} caracteres."
        )
    return termino


DURACION_MAXIMA_BUSQUEDA_MS = 3_600_000  # una hora: mas que eso es un error de captura


def busqueda_control(datos: dict) -> dict:
    """Valida POST /busquedas: una medicion manual que sirve de referencia."""
    faltantes = [c for c in ("object_id", "duracion_ms") if c not in datos]
    if faltantes:
        raise ErrorValidacion(
            "Faltan campos obligatorios.", {"campos": sorted(faltantes)}
        )
    if datos.get("modo", "control") != "control":
        raise ErrorValidacion(
            "Aqui solo se registran mediciones manuales ('control'); las busquedas "
            "con el sistema las abre POST /objetos/{object_id}/localizar."
        )
    return {
        "object_id": identificador(datos["object_id"], "object_id"),
        "duracion_ms": entero(
            datos["duracion_ms"], "duracion_ms", minimo=1, maximo=DURACION_MAXIMA_BUSQUEDA_MS
        ),
    }


def duracion_localizacion(datos: dict) -> int:
    if "duracion_segundos" not in datos:
        return config.duracion_led_defecto()
    return entero(
        datos["duracion_segundos"],
        "duracion_segundos",
        minimo=1,
        maximo=config.duracion_led_maxima(),
    )


def limite_pagina(event: dict) -> int:
    bruto = parametro_query(event, "limite")
    if bruto is None:
        return config.limite_pagina_defecto()
    try:
        valor = int(bruto)
    except ValueError as exc:
        raise ErrorValidacion("'limite' debe ser un numero entero.") from exc
    return entero(valor, "limite", minimo=1, maximo=config.limite_pagina_maximo())
