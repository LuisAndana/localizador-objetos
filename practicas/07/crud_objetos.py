"""
Práctica 7 · Base de datos no relacional y operaciones desde código
Foráneos Team · Localizador inteligente de objetos

Función Lambda que hace las cuatro operaciones básicas (insertar, consultar,
actualizar y eliminar) sobre la tabla DynamoDB localizador-objetos-p07.

Credenciales: la función se ejecuta con el rol de servicio
ForaneosTeam-Lambda-DynamoDB. boto3 toma de forma automática las credenciales
temporales que AWS entrega a ese rol; en este archivo NO hay llaves de acceso.

Diseño de la tabla (derivado del patrón de acceso):
  - Clave de partición: object_id
  - Índice global almacen-index: partición almacen_id, ordenación ubicacion

Cada prueba manda un evento con el campo "op":
  insertar · consultar · plano · actualizar · eliminar · buscar_sin_clave
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

TABLA = os.environ.get("TABLA", "localizador-objetos-p07")
INDICE_ALMACEN = "almacen-index"

dynamodb = boto3.resource("dynamodb")
tabla = dynamodb.Table(TABLA)


def ahora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def a_json(valor):
    """DynamoDB regresa los números como Decimal; los convertimos para imprimirlos."""
    if isinstance(valor, list):
        return [a_json(v) for v in valor]
    if isinstance(valor, dict):
        return {k: a_json(v) for k, v in valor.items()}
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    return valor


def capacidad(respuesta):
    """Unidades de capacidad que consumió la operación (lo que se cobra en bajo demanda)."""
    c = respuesta.get("ConsumedCapacity") or {}
    return c.get("CapacityUnits")


# ---------------------------------------------------------------- insertar
def insertar(evento):
    resultados = []
    for o in evento["objetos"]:
        item = {
            "object_id": o["object_id"],
            "nombre": o["nombre"],
            "categoria": o["categoria"],
            "almacen_id": o["almacen_id"],
            "pasillo": o["pasillo"],
            "anaquel": o["anaquel"],
            "nivel": o["nivel"],
            "columna": o["columna"],
            # clave de ordenación del índice: el plano sale ordenado por ubicación
            "ubicacion": f'{o["pasillo"]}#{o["anaquel"]}#{o["nivel"]}#{o["columna"]}',
            "posicion_led": o["posicion_led"],
            "color_indicador": o.get("color_indicador", "#00A0FF"),
            "cantidad": o["cantidad"],
            "ultima_actualizacion": ahora(),
        }
        try:
            r = tabla.put_item(
                Item=item,
                # no sobrescribir un objeto que ya existe
                ConditionExpression="attribute_not_exists(object_id)",
                ReturnConsumedCapacity="TOTAL",
            )
            resultados.append({"object_id": item["object_id"], "estado": "insertado",
                               "unidades_escritura": capacidad(r)})
        except ClientError as e:
            resultados.append({"object_id": item["object_id"], "estado": "rechazado",
                               "motivo": e.response["Error"]["Code"]})
    return {"insertados": sum(r["estado"] == "insertado" for r in resultados), "detalle": resultados}


# ---------------------------------------------------------------- consultar (consulta principal)
def consultar(evento):
    """Dado el object_id, obtener su ubicación, su LED y su existencia (GetItem por la clave)."""
    r = tabla.get_item(Key={"object_id": evento["object_id"]}, ReturnConsumedCapacity="TOTAL")
    item = r.get("Item")
    if not item:
        return {"object_id": evento["object_id"], "encontrado": False, "unidades_lectura": capacidad(r)}
    return {
        "encontrado": True,
        "objeto": item["nombre"],
        "ubicacion": {k: item[k] for k in ("almacen_id", "pasillo", "anaquel", "nivel", "columna")},
        "posicion_led": item["posicion_led"],
        "cantidad": item["cantidad"],
        "unidades_lectura": capacidad(r),
    }


# ---------------------------------------------------------------- plano (índice almacen-index)
def plano(evento):
    """Dado un almacén, obtener sus objetos ordenados por ubicación (Query sobre el índice)."""
    r = tabla.query(
        IndexName=INDICE_ALMACEN,
        KeyConditionExpression=Key("almacen_id").eq(evento["almacen_id"]),
        ReturnConsumedCapacity="TOTAL",
    )
    return {
        "almacen_id": evento["almacen_id"],
        "elementos_devueltos": r["Count"],
        "elementos_leidos": r["ScannedCount"],
        "unidades_lectura": capacidad(r),
        "objetos": [f'{i["ubicacion"]}  {i["nombre"]} ({i["cantidad"]})' for i in r["Items"]],
    }


# ---------------------------------------------------------------- actualizar
def actualizar(evento):
    """Registra una entrada o una salida. Una salida nunca deja la existencia en negativo."""
    oid = evento["object_id"]
    if "salida" in evento:
        n = int(evento["salida"])
        expr = "SET cantidad = cantidad - :n, ultima_actualizacion = :t"
        cond = "attribute_exists(object_id) AND cantidad >= :n"
    else:
        n = int(evento["entrada"])
        expr = "SET cantidad = cantidad + :n, ultima_actualizacion = :t"
        cond = "attribute_exists(object_id)"
    try:
        r = tabla.update_item(
            Key={"object_id": oid},
            UpdateExpression=expr,
            ConditionExpression=cond,
            ExpressionAttributeValues={":n": n, ":t": ahora()},
            ReturnValues="ALL_NEW",
            ReturnConsumedCapacity="TOTAL",
        )
        nuevo = r["Attributes"]
        return {"object_id": oid, "estado": "actualizado", "objeto": nuevo["nombre"],
                "cantidad_nueva": nuevo["cantidad"], "unidades_escritura": capacidad(r)}
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"object_id": oid, "estado": "rechazado",
                    "motivo": "no hay existencias suficientes o el objeto no existe; no se cambió nada"}
        raise


# ---------------------------------------------------------------- eliminar
def eliminar(evento):
    """Borra un objeto solo si su existencia es 0 (misma regla que el código del proyecto)."""
    oid = evento["object_id"]
    try:
        r = tabla.delete_item(
            Key={"object_id": oid},
            ConditionExpression="attribute_exists(object_id) AND cantidad = :cero",
            ExpressionAttributeValues={":cero": 0},
            ReturnValues="ALL_OLD",
            ReturnConsumedCapacity="TOTAL",
        )
        return {"object_id": oid, "estado": "eliminado", "objeto": r["Attributes"]["nombre"],
                "unidades_escritura": capacidad(r)}
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"object_id": oid, "estado": "rechazado",
                    "motivo": "solo se elimina un objeto sin existencias, o el objeto no existe"}
        raise


# ---------------------------------------------------------------- consulta ineficiente (paso 7)
def buscar_sin_clave(evento):
    """Busca por nombre: no usa la clave, así que DynamoDB tendría que recorrer toda la tabla (Scan)."""
    try:
        r = tabla.scan(FilterExpression=Attr("nombre").contains(evento["texto"]),
                       ReturnConsumedCapacity="TOTAL")
        return {"texto": evento["texto"], "elementos_devueltos": r["Count"],
                "elementos_leidos": r["ScannedCount"], "unidades_lectura": capacidad(r)}
    except ClientError as e:
        return {"texto": evento["texto"], "estado": "denegado",
                "error": e.response["Error"]["Code"],
                "explicacion": "el rol de servicio no incluye dynamodb:Scan, a propósito (práctica 2)"}


OPERACIONES = {
    "insertar": insertar,
    "consultar": consultar,
    "plano": plano,
    "actualizar": actualizar,
    "eliminar": eliminar,
    "buscar_sin_clave": buscar_sin_clave,
}


def lambda_handler(evento, contexto):
    op = evento.get("op")
    if op not in OPERACIONES:
        return {"error": f"op desconocida: {op}", "validas": list(OPERACIONES)}
    identidad = boto3.client("sts").get_caller_identity()["Arn"]
    resultado = a_json(OPERACIONES[op](evento))
    respuesta = {"op": op, "tabla": TABLA, "ejecutado_como": identidad, "resultado": resultado}
    print(json.dumps(respuesta, ensure_ascii=False))
    return respuesta
