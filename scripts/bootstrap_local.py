"""Crea y siembra las tablas en DynamoDB Local para desarrollo.

Idempotente: si las tablas ya existen no falla, y los objetos de ejemplo se
escriben con PutItem (sobrescriben su propia copia, no duplican).

  python scripts/bootstrap_local.py
  python scripts/bootstrap_local.py --reset     # borra y recrea las tablas

Los datos sembrados son placeholders de demostracion, no datos reales.
"""

import argparse
import os
import sys
import unicodedata

import boto3
from botocore.exceptions import ClientError

ENDPOINT = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
REGION = os.environ.get("AWS_REGION", "us-east-1")
PREFIJO = os.environ.get("PREFIJO_TABLAS", "localizador-objetos-dev")

TABLA_OBJETOS = f"{PREFIJO}-Objetos"
TABLA_CATEGORIAS = f"{PREFIJO}-Categorias"
INDICE_CATEGORIA = "categoria-index"

CATEGORIAS_DEMO = [
    {
        "categoria_id": "herramientas",
        "nombre": "Herramientas",
        "descripcion": "Herramienta manual y electrica",
    },
    {
        "categoria_id": "refacciones",
        "nombre": "Refacciones",
        "descripcion": "Piezas de repuesto",
    },
    {
        "categoria_id": "consumibles",
        "nombre": "Consumibles",
        "descripcion": "Material de uso y desgaste",
    },
]

OBJETOS_DEMO = [
    {
        "object_id": "obj-demo-001",
        "nombre": "Taladro percutor",
        "categoria": "herramientas",
        "almacen_id": "almacen-01",
        "pasillo": "A",
        "anaquel": "3",
        "nivel": "2",
        "columna": "A",
        "posicion_led": 42,
        "color_indicador": "#00FF00",
        "ultima_actualizacion": "2026-01-01T00:00:00+00:00",
    },
    {
        "object_id": "obj-demo-002",
        "nombre": "Llave de torque",
        "categoria": "herramientas",
        "almacen_id": "almacen-01",
        "pasillo": "A",
        "anaquel": "4",
        "nivel": "1",
        "columna": "B",
        "posicion_led": 57,
        "color_indicador": "#00AAFF",
        "ultima_actualizacion": "2026-01-01T00:00:00+00:00",
    },
    {
        "object_id": "obj-demo-003",
        "nombre": "Rodamiento 6204",
        "categoria": "refacciones",
        "almacen_id": "almacen-02",
        "pasillo": "C",
        "anaquel": "1",
        "nivel": "3",
        "columna": "C",
        "posicion_led": 8,
        "color_indicador": "#FFAA00",
        "ultima_actualizacion": "2026-01-01T00:00:00+00:00",
    },
]


def _normalizar(texto: str) -> str:
    """Igual que localizador.validacion.normalizar_busqueda (minusculas, sin acentos)."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.lower().split())


def _cliente():
    return boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "local"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "local"),
    )


def _existe(dynamodb, nombre: str) -> bool:
    try:
        dynamodb.Table(nombre).load()
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def crear_tabla_objetos(dynamodb) -> None:
    if _existe(dynamodb, TABLA_OBJETOS):
        print(f"  = {TABLA_OBJETOS} ya existe")
        return
    tabla = dynamodb.create_table(
        TableName=TABLA_OBJETOS,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "object_id", "AttributeType": "S"},
            {"AttributeName": "categoria", "AttributeType": "S"},
            {"AttributeName": "nombre", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "object_id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": INDICE_CATEGORIA,
                "KeySchema": [
                    {"AttributeName": "categoria", "KeyType": "HASH"},
                    {"AttributeName": "nombre", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    tabla.wait_until_exists()
    print(f"  + {TABLA_OBJETOS} creada (GSI {INDICE_CATEGORIA})")


def crear_tabla_categorias(dynamodb) -> None:
    if _existe(dynamodb, TABLA_CATEGORIAS):
        print(f"  = {TABLA_CATEGORIAS} ya existe")
        return
    tabla = dynamodb.create_table(
        TableName=TABLA_CATEGORIAS,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "categoria_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "categoria_id", "KeyType": "HASH"}],
    )
    tabla.wait_until_exists()
    print(f"  + {TABLA_CATEGORIAS} creada")


def sembrar(dynamodb) -> None:
    tabla_obj = dynamodb.Table(TABLA_OBJETOS)
    for item in OBJETOS_DEMO:
        # La API guarda esta copia normalizada al crear; aqui se escribe directo
        # en la tabla, asi que hay que agregarla para que la busqueda los encuentre.
        tabla_obj.put_item(Item={**item, "nombre_busqueda": _normalizar(item["nombre"])})
    tabla_cat = dynamodb.Table(TABLA_CATEGORIAS)
    for item in CATEGORIAS_DEMO:
        tabla_cat.put_item(Item=item)
    print(
        f"  + sembrados {len(OBJETOS_DEMO)} objetos y "
        f"{len(CATEGORIAS_DEMO)} categorias de demostracion"
    )


def reiniciar(dynamodb) -> None:
    for nombre in (TABLA_OBJETOS, TABLA_CATEGORIAS):
        if _existe(dynamodb, nombre):
            tabla = dynamodb.Table(nombre)
            tabla.delete()
            tabla.wait_until_not_exists()
            print(f"  - {nombre} eliminada")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="Borra las tablas antes de crearlas."
    )
    args = parser.parse_args()

    print(f"DynamoDB Local: {ENDPOINT}")
    dynamodb = _cliente()
    try:
        if args.reset:
            reiniciar(dynamodb)
        crear_tabla_objetos(dynamodb)
        crear_tabla_categorias(dynamodb)
        sembrar(dynamodb)
    except ClientError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: no se pudo contactar DynamoDB Local en {ENDPOINT}", file=sys.stderr)
        print(f"       {exc}", file=sys.stderr)
        print("       Arrancalo con: docker run -p 8000:8000 amazon/dynamodb-local", file=sys.stderr)
        return 1

    print("Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
