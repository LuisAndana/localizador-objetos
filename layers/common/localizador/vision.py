"""Convierte lo que ve Amazon Rekognition en una propuesta de alta.

La IA solo PROPONE: el resultado prellena el formulario de registro y una persona
lo confirma o lo corrige antes de guardar. Nada de aqui escribe un objeto ni
enciende un LED.

Rekognition devuelve etiquetas en ingles ("Drill", "Tool") con su confianza, y
lineas de texto leidas en la foto ("6204-2RS"). Aqui se traducen las etiquetas
al vocabulario del almacen, se elige la mas especifica, se busca una categoria
del catalogo que le corresponda y se aparta el texto que parece un numero de
parte. Es una funcion pura: se prueba sin AWS.
"""

import re
from decimal import Decimal

from .validacion import normalizar_busqueda

# Umbrales de la propuesta del proyecto (seccion 8): por encima de 85 la
# sugerencia es fiable; entre 60 y 85, hay que revisarla; debajo de 60, no se
# prellena nada salvo que la persona lo pida.
UMBRAL_ALTA = 85.0
UMBRAL_MEDIA = 60.0

CONFIANZA_MINIMA_TEXTO = 80.0
MAXIMO_ETIQUETAS = 5
MAXIMO_TEXTOS = 5

# Etiqueta de Rekognition -> nombre en el almacen.
TRADUCCIONES = {
    "drill": "Taladro",
    "power drill": "Taladro electrico",
    "hammer": "Martillo",
    "wrench": "Llave",
    "screwdriver": "Desarmador",
    "pliers": "Pinzas",
    "saw": "Sierra",
    "hand saw": "Serrucho",
    "chainsaw": "Motosierra",
    "tape measure": "Flexometro",
    "level": "Nivel",
    "tool": "Herramienta",
    "hand tool": "Herramienta manual",
    "power tool": "Herramienta electrica",
    "screw": "Tornillo",
    "bolt": "Perno",
    "nut": "Tuerca",
    "nail": "Clavo",
    "glove": "Guantes",
    "tape": "Cinta",
    "duct tape": "Cinta de ducto",
    "bottle": "Botella",
    "spray can": "Aerosol",
    "battery": "Bateria",
    "cable": "Cable",
    "wire": "Cable",
    "plug": "Clavija",
    "adapter": "Adaptador",
    "electrical device": "Dispositivo electrico",
    "circuit board": "Tarjeta electronica",
    "printed circuit board": "Tarjeta electronica",
    "multimeter": "Multimetro",
    "voltmeter": "Multimetro",
    "electronics": "Equipo electronico",
    "monitor": "Monitor",
    "light bulb": "Foco",
    "bearing": "Rodamiento",
    "ball bearing": "Rodamiento",
    "gear": "Engrane",
    "belt": "Banda",
    "filter": "Filtro",
    "engine": "Motor",
    "motor": "Motor",
    "pipe": "Tubo",
    "valve": "Valvula",
    "spring": "Resorte",
    "helmet": "Casco",
    "hardhat": "Casco de seguridad",
    "goggles": "Lentes de seguridad",
    "safety vest": "Chaleco de seguridad",
    "mask": "Mascarilla",
    "boot": "Botas",
    "box": "Caja",
}

# Etiquetas demasiado generales para nombrar un objeto ("Metal", "Indoors").
# Sirven si no hay nada mejor, pero nunca le ganan a una especifica.
GENERICAS = {
    "tool", "hand tool", "power tool", "electronics", "electrical device", "device",
    "machine", "metal", "plastic", "wood", "indoors", "shelf", "furniture", "text",
    "label", "person", "hand", "finger", "box", "cardboard", "aluminium", "steel",
    "brass", "chrome", "mechanical", "hardware", "accessories",
}

# Etiqueta -> categorias candidatas, en orden de preferencia. Solo se propone
# una que exista en el catalogo, asi que nombres de varios catalogos conviven.
CATEGORIAS_POR_ETIQUETA = {
    **dict.fromkeys(
        ["drill", "power drill", "hammer", "wrench", "screwdriver", "pliers", "saw",
         "hand saw", "chainsaw", "tape measure", "level", "tool", "hand tool", "power tool"],
        ["herramientas"],
    ),
    **dict.fromkeys(
        ["battery", "cable", "wire", "plug", "adapter", "electrical device", "circuit board",
         "printed circuit board", "multimeter", "voltmeter", "electronics", "monitor",
         "light bulb"],
        ["electronica"],
    ),
    **dict.fromkeys(
        ["bearing", "ball bearing", "gear", "belt", "filter", "engine", "motor", "pipe",
         "valve", "spring", "machine"],
        ["refacciones"],
    ),
    **dict.fromkeys(
        ["screw", "bolt", "nut", "nail", "glove", "tape", "duct tape", "bottle", "spray can"],
        ["consumibles"],
    ),
    **dict.fromkeys(
        ["helmet", "hardhat", "goggles", "safety vest", "mask", "boot"],
        ["equipo-de-proteccion", "seguridad", "consumibles"],
    ),
}

# Un numero de parte: al menos 3 caracteres, con algun digito ("6204", "M6-20").
REGEX_CODIGO = re.compile(r"^[A-Z0-9][A-Z0-9\-./]{2,29}$")


def nivel_de_confianza(confianza: float) -> str:
    if confianza >= UMBRAL_ALTA:
        return "alta"
    if confianza >= UMBRAL_MEDIA:
        return "media"
    return "baja"


def _etiquetas_ordenadas(etiquetas: list[dict]) -> list[tuple[str, float]]:
    """(nombre en minusculas, confianza), de la mas especifica y segura a la menos."""
    vistas: dict[str, float] = {}
    for e in etiquetas:
        nombre = str(e.get("Name", "")).strip().lower()
        if nombre:
            vistas[nombre] = max(vistas.get(nombre, 0.0), float(e.get("Confidence", 0.0)))
    return sorted(vistas.items(), key=lambda par: (par[0] in GENERICAS, -par[1]))


def _categoria(candidatas: list[str], categorias: set[str]) -> str | None:
    for etiqueta in candidatas:
        for categoria in CATEGORIAS_POR_ETIQUETA.get(etiqueta, []):
            if categoria in categorias:
                return categoria
    return None


def _textos(detecciones: list[dict]) -> list[str]:
    lineas = []
    for d in detecciones:
        if d.get("Type") != "LINE" or float(d.get("Confidence", 0.0)) < CONFIANZA_MINIMA_TEXTO:
            continue
        texto = " ".join(str(d.get("DetectedText", "")).split())
        if texto and texto not in lineas:
            lineas.append(texto)
    return lineas[:MAXIMO_TEXTOS]


def _codigo(textos: list[str]) -> str | None:
    for linea in textos:
        for palabra in linea.upper().split():
            if REGEX_CODIGO.match(palabra) and any(c.isdigit() for c in palabra):
                return palabra
    return None


def proponer(etiquetas: list[dict], detecciones_texto: list[dict], categorias: set[str]) -> dict:
    """Arma la sugerencia de alta a partir de DetectLabels y DetectText.

    `categorias` son los categoria_id del catalogo: solo se propone una existente.
    """
    ordenadas = _etiquetas_ordenadas(etiquetas)
    textos = _textos(detecciones_texto)
    codigo = _codigo(textos)

    conocidas = [(n, c) for n, c in ordenadas if n in TRADUCCIONES]
    principal = conocidas[0] if conocidas else (ordenadas[0] if ordenadas else None)

    nombre = None
    confianza = 0.0
    if principal:
        clave, confianza = principal
        nombre = TRADUCCIONES.get(clave, clave.capitalize())
        if codigo and codigo.lower() not in normalizar_busqueda(nombre):
            nombre = f"{nombre} {codigo}"

    return {
        "nombre_sugerido": nombre,
        "categoria_sugerida": _categoria([n for n, _ in ordenadas], categorias),
        "codigo_detectado": codigo,
        "confianza": round(confianza, 1),
        "nivel": nivel_de_confianza(confianza),
        "etiquetas": [
            {"nombre": TRADUCCIONES.get(n, n.capitalize()), "original": n, "confianza": round(c, 1)}
            for n, c in ordenadas[:MAXIMO_ETIQUETAS]
        ],
        "textos": textos,
    }


def para_dynamo(valor):
    """DynamoDB no acepta float: los convierte a Decimal (recursivo)."""
    if isinstance(valor, float):
        return Decimal(str(valor))
    if isinstance(valor, dict):
        return {k: para_dynamo(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [para_dynamo(v) for v in valor]
    return valor
