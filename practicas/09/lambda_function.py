"""Recalcula el resumen de metricas al confirmarse una busqueda.

Foraneos Team · Practica 9 · Localizador inteligente de objetos

Dos formas de invocacion:
- DynamoDB Streams (tabla de busquedas): suma cada busqueda recien confirmada.
- URL de funcion con IAM (HTTP GET): devuelve el resumen.

Credenciales: la funcion usa su rol de ejecucion; no hay llaves en el codigo.
"""
import json
import os

import boto3

tabla_resumen = boto3.resource("dynamodb").Table(os.environ["TABLA_RESUMEN"])
CLAVE = "global"


def _recien_confirmada(record):
    nueva = record["dynamodb"].get("NewImage", {})
    antigua = record["dynamodb"].get("OldImage", {})
    confirmada_ahora = nueva.get("confirmada_en", {}).get("S", "")
    confirmada_antes = antigua.get("confirmada_en", {}).get("S", "")
    return (record.get("eventName") in ("INSERT", "MODIFY")
            and bool(confirmada_ahora) and not confirmada_antes)


def _sumar(record):
    duracion = int(record["dynamodb"]["NewImage"]["duracion_ms"]["N"])
    tabla_resumen.update_item(
        Key={"clave": CLAVE},
        # "total" es palabra reservada de DynamoDB: se usa el alias #total
        UpdateExpression="ADD #total :uno, suma_ms :d",
        ExpressionAttributeNames={"#total": "total"},
        ExpressionAttributeValues={":uno": 1, ":d": duracion},
    )


def _leer():
    item = tabla_resumen.get_item(Key={"clave": CLAVE}).get("Item", {})
    total = int(item.get("total", 0))
    suma = int(item.get("suma_ms", 0))
    return {"total_busquedas": total,
            "promedio_ms": round(suma / total) if total else None}


def lambda_handler(event, context):
    if "Records" in event:
        sumadas = 0
        for record in event["Records"]:
            if _recien_confirmada(record):
                _sumar(record)
                sumadas += 1
        return {"procesados": len(event["Records"]), "sumadas": sumadas}

    if event.get("requestContext", {}).get("http", {}).get("method") != "GET":
        return {"statusCode": 405, "body": json.dumps({"error": "metodo no permitido"})}

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(_leer()),
    }
