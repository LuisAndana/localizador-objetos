"""Resumen del indicador de tiempo de localizacion.

Funcion pura sobre las busquedas ya cronometradas: compara el metodo manual
(`control`) contra el sistema y calcula la reduccion, que es la meta del acta
constitutiva (40 %). No conoce DynamoDB ni SQLite.
"""

from datetime import datetime

META_REDUCCION_PCT = 40


def duracion_ms(iniciada_en: str, confirmada_en: str) -> int:
    """Milisegundos entre dos marcas ISO. Devuelve 0 si alguna no es valida."""
    try:
        inicio = datetime.fromisoformat(iniciada_en)
        fin = datetime.fromisoformat(confirmada_en)
    except (TypeError, ValueError):
        return 0
    return max(0, round((fin - inicio).total_seconds() * 1000))


def _percentil(ordenados: list[int], fraccion: float) -> int:
    """Percentil por el metodo del vecino mas cercano.

    Con muestras de 20 busquedas no vale la pena interpolar: el indice redondeado
    da el mismo veredicto y es mas facil de explicar en la defensa.
    """
    if not ordenados:
        return 0
    indice = min(len(ordenados) - 1, max(0, round(fraccion * (len(ordenados) - 1))))
    return ordenados[indice]


def _estadisticas(duraciones: list[int]) -> dict:
    ordenados = sorted(duraciones)
    if not ordenados:
        return {"muestras": 0, "promedio_ms": 0, "mediana_ms": 0, "p90_ms": 0, "minimo_ms": 0, "maximo_ms": 0}
    return {
        "muestras": len(ordenados),
        "promedio_ms": round(sum(ordenados) / len(ordenados)),
        "mediana_ms": _percentil(ordenados, 0.5),
        "p90_ms": _percentil(ordenados, 0.9),
        "minimo_ms": ordenados[0],
        "maximo_ms": ordenados[-1],
    }


def resumir(busquedas: list[dict]) -> dict:
    """Agrupa las busquedas confirmadas por modo y calcula la reduccion."""
    duraciones: dict[str, list[int]] = {"sistema": [], "control": []}
    abiertas = 0

    for item in busquedas:
        if not item.get("confirmada_en"):
            abiertas += 1
            continue
        modo = item.get("modo", "sistema")
        duraciones.setdefault(modo, []).append(int(item.get("duracion_ms", 0)))

    con_sistema = _estadisticas(duraciones["sistema"])
    manual = _estadisticas(duraciones["control"])

    reduccion = None
    if con_sistema["muestras"] and manual["muestras"] and manual["promedio_ms"]:
        reduccion = round(
            (1 - con_sistema["promedio_ms"] / manual["promedio_ms"]) * 100, 1
        )

    return {
        "con_sistema": con_sistema,
        "manual": manual,
        "busquedas_abiertas": abiertas,
        "reduccion_pct": reduccion,
        "meta_pct": META_REDUCCION_PCT,
        # None mientras falte alguna de las dos muestras: sin referencia manual
        # no hay nada contra que comparar.
        "cumple_meta": None if reduccion is None else reduccion >= META_REDUCCION_PCT,
    }
