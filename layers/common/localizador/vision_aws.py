"""Adaptadores de AWS para la identificacion por foto: S3, Rekognition y DynamoDB."""

import boto3
from botocore.config import Config as ConfigBoto
from botocore.exceptions import ClientError

from . import config, vision
from .errores import ErrorNoEncontrado
from .modelos import ahora_iso_preciso
from .repositorios import _recurso_dynamodb

_CONFIG_BOTO = ConfigBoto(retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=2, read_timeout=10)

# Una foto de telefono reducida en el navegador ronda 300 KB; 5 MB deja margen y
# frena subidas abusivas. Rekognition acepta hasta 15 MB desde S3.
TAMANO_MAXIMO_FOTO = 5 * 1024 * 1024
VIGENCIA_URL_SEGUNDOS = 300

MAXIMO_ETIQUETAS = 15
CONFIANZA_MINIMA_ETIQUETA = 55.0


class RepositorioIdentificaciones:
    def __init__(self, nombre_tabla: str | None = None):
        self._tabla = _recurso_dynamodb().Table(nombre_tabla or config.tabla_identificaciones())

    def crear(self, identificacion: dict) -> dict:
        self._tabla.put_item(Item=identificacion)
        return identificacion

    def obtener(self, identificacion_id: str) -> dict:
        item = self._tabla.get_item(Key={"identificacion_id": identificacion_id}).get("Item")
        if not item:
            raise ErrorNoEncontrado(f"No existe ninguna identificacion con id '{identificacion_id}'.")
        return item

    def _actualizar(self, identificacion_id: str, valores: dict) -> None:
        nombres = {f"#c{i}": campo for i, campo in enumerate(valores)}
        expresion = {f":v{i}": valor for i, valor in enumerate(valores.values())}
        try:
            self._tabla.update_item(
                Key={"identificacion_id": identificacion_id},
                UpdateExpression="SET " + ", ".join(f"{n} = {v}" for n, v in zip(nombres, expresion)),
                ExpressionAttributeNames=nombres,
                ExpressionAttributeValues=expresion,
                # Solo solicitudes creadas por la API: una foto subida a mano al
                # bucket no crea registros nuevos.
                ConditionExpression="attribute_exists(identificacion_id)",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ErrorNoEncontrado(
                    f"No existe ninguna identificacion con id '{identificacion_id}'."
                ) from exc
            raise

    def completar(self, identificacion_id: str, propuesta: dict) -> None:
        self._actualizar(
            identificacion_id,
            {"estado": "lista", "propuesta": vision.para_dynamo(propuesta), "procesada_en": ahora_iso_preciso()},
        )

    def fallar(self, identificacion_id: str, motivo: str) -> None:
        self._actualizar(
            identificacion_id, {"estado": "error", "motivo": motivo, "procesada_en": ahora_iso_preciso()}
        )


class AlmacenFotosS3:
    def __init__(self, bucket: str | None = None, cliente=None):
        self._bucket = bucket or config.bucket_fotos()
        self._cliente = cliente or boto3.client("s3", config=_CONFIG_BOTO)

    def url_subida(self, clave: str) -> dict:
        """POST prefirmado: S3 mismo rechaza otro tipo de archivo o un tamano mayor."""
        datos = self._cliente.generate_presigned_post(
            Bucket=self._bucket,
            Key=clave,
            Fields={"Content-Type": "image/jpeg"},
            Conditions=[
                {"Content-Type": "image/jpeg"},
                ["content-length-range", 1, TAMANO_MAXIMO_FOTO],
            ],
            ExpiresIn=VIGENCIA_URL_SEGUNDOS,
        )
        return {"url": datos["url"], "campos": datos["fields"], "tamano_maximo": TAMANO_MAXIMO_FOTO}


class ReconocimientoRekognition:
    def __init__(self, bucket: str | None = None, cliente=None):
        self._bucket = bucket or config.bucket_fotos()
        self._cliente = cliente or boto3.client("rekognition", config=_CONFIG_BOTO)

    def analizar(self, clave: str) -> tuple[list[dict], list[dict]]:
        # Rekognition lee la foto directo de S3: la imagen no pasa por la Lambda.
        imagen = {"S3Object": {"Bucket": self._bucket, "Name": clave}}
        etiquetas = self._cliente.detect_labels(
            Image=imagen, MaxLabels=MAXIMO_ETIQUETAS, MinConfidence=CONFIANZA_MINIMA_ETIQUETA
        ).get("Labels", [])
        textos = self._cliente.detect_text(Image=imagen).get("TextDetections", [])
        return etiquetas, textos
