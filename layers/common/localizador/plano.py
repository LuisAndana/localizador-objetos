"""Arma el plano 2D del almacen a partir de los objetos.

Funciones puras: reciben los items tal como salen del repositorio y devuelven
la estructura que dibuja el mapa. No conocen DynamoDB ni SQLite, por eso el
plano sale identico en AWS y en local.
"""

from typing import Any

CAMPOS_OBJETO = ("object_id", "nombre", "categoria", "posicion_led", "color_indicador")


def _clave_orden(valor: str) -> tuple[int, int, str]:
    """Orden natural: el anaquel 10 va despues del 9, no entre el 1 y el 2."""
    if valor.isdigit():
        return (0, int(valor), "")
    return (1, 0, valor.lower())


def _resumen_objeto(item: dict) -> dict:
    datos = {campo: item.get(campo) for campo in CAMPOS_OBJETO}
    # DynamoDB devuelve Decimal; el mapa lo usa como numero de LED.
    datos["posicion_led"] = int(datos["posicion_led"] or 0)
    return datos


def _niveles(por_nivel: dict[str, list[dict]]) -> list[dict]:
    """Niveles ordenados de abajo hacia arriba, incluidos los vacios.

    Un anaquel con objetos solo en los niveles 1 y 3 se dibuja con el 2 vacio:
    el mapa debe parecerse al anaquel real, no solo a lo que esta ocupado.
    """
    numericos = [int(n) for n in por_nivel if n.isdigit()]
    faltantes: set[str] = set()
    if numericos:
        faltantes = {str(n) for n in range(1, max(numericos) + 1)} - set(por_nivel)
    return [
        {
            "nivel": nivel,
            "objetos": sorted(por_nivel.get(nivel, []), key=lambda o: o["posicion_led"]),
        }
        for nivel in sorted(set(por_nivel) | faltantes, key=_clave_orden)
    ]


def construir(almacen_id: str, objetos: list[dict]) -> dict:
    """Agrupa los objetos del almacen en pasillos -> anaqueles -> niveles."""
    pasillos: dict[str, dict[str, dict[str, list[dict]]]] = {}
    for item in objetos:
        anaqueles = pasillos.setdefault(str(item["pasillo"]), {})
        niveles = anaqueles.setdefault(str(item["anaquel"]), {})
        niveles.setdefault(str(item["nivel"]), []).append(_resumen_objeto(item))

    return {
        "almacen_id": almacen_id,
        "total_objetos": len(objetos),
        "total_pasillos": len(pasillos),
        "pasillos": [
            {
                "pasillo": pasillo,
                "total_objetos": sum(
                    len(objs) for niveles in anaqueles.values() for objs in niveles.values()
                ),
                "anaqueles": [
                    {
                        "anaquel": anaquel,
                        "total_objetos": sum(len(objs) for objs in niveles.values()),
                        "niveles": _niveles(niveles),
                    }
                    for anaquel, niveles in sorted(anaqueles.items(), key=lambda par: _clave_orden(par[0]))
                ],
            }
            for pasillo, anaqueles in sorted(pasillos.items(), key=lambda par: _clave_orden(par[0]))
        ],
    }


def resumir_almacenes(items: list[dict[str, Any]]) -> list[dict]:
    """Cuenta objetos y pasillos por almacen. En SQLite lo hace un GROUP BY."""
    resumen: dict[str, dict] = {}
    for item in items:
        almacen = str(item["almacen_id"])
        datos = resumen.setdefault(almacen, {"total_objetos": 0, "pasillos": set()})
        datos["total_objetos"] += 1
        datos["pasillos"].add(str(item["pasillo"]))
    return [
        {
            "almacen_id": almacen,
            "total_objetos": datos["total_objetos"],
            "total_pasillos": len(datos["pasillos"]),
        }
        for almacen, datos in sorted(resumen.items())
    ]
