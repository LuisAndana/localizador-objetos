"""Identificacion por foto: propuesta a partir de Rekognition, servicio y adaptadores."""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from botocore.stub import Stubber

from localizador import vision
from localizador.errores import ErrorNoEncontrado
from localizador.servicios import ServicioIdentificacion

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = {"herramientas", "refacciones", "consumibles", "electronica"}


def etiqueta(nombre: str, confianza: float) -> dict:
    return {"Name": nombre, "Confidence": confianza}


def linea(texto: str, confianza: float = 99.0) -> dict:
    return {"DetectedText": texto, "Type": "LINE", "Confidence": confianza}


# --- Propuesta (funcion pura) ---------------------------------------------------------


def test_taladro_con_confianza_alta():
    p = vision.proponer(
        [etiqueta("Tool", 99.5), etiqueta("Drill", 97.2), etiqueta("Power Drill", 90.1)], [], CATALOGO
    )
    assert p["nombre_sugerido"] == "Taladro"
    assert p["categoria_sugerida"] == "herramientas"
    assert p["confianza"] == 97.2
    assert p["nivel"] == "alta"


def test_lo_especifico_le_gana_a_lo_generico_aunque_tenga_menos_confianza():
    p = vision.proponer([etiqueta("Metal", 99.9), etiqueta("Hammer", 70.0)], [], CATALOGO)
    assert p["nombre_sugerido"] == "Martillo"
    assert p["nivel"] == "media"


def test_el_numero_de_parte_se_agrega_al_nombre():
    p = vision.proponer(
        [etiqueta("Ball Bearing", 92.0)],
        [linea("SKF"), linea("6204-2RS"), {"DetectedText": "6204-2RS", "Type": "WORD", "Confidence": 99}],
        CATALOGO,
    )
    assert p["codigo_detectado"] == "6204-2RS"
    assert p["nombre_sugerido"] == "Rodamiento 6204-2RS"
    assert p["categoria_sugerida"] == "refacciones"
    assert p["textos"] == ["SKF", "6204-2RS"]


def test_texto_dudoso_se_descarta():
    p = vision.proponer([etiqueta("Screw", 90.0)], [linea("M6X20", 50.0)], CATALOGO)
    assert p["codigo_detectado"] is None
    assert p["textos"] == []


def test_solo_propone_categorias_que_existen():
    p = vision.proponer([etiqueta("Hardhat", 95.0)], [], {"consumibles"})
    assert p["categoria_sugerida"] == "consumibles"
    p = vision.proponer([etiqueta("Hardhat", 95.0)], [], {"herramientas"})
    assert p["categoria_sugerida"] is None


def test_etiqueta_sin_traduccion_se_usa_tal_cual():
    p = vision.proponer([etiqueta("Stapler", 88.0)], [], CATALOGO)
    assert p["nombre_sugerido"] == "Stapler"
    assert p["categoria_sugerida"] is None


def test_sin_etiquetas_no_inventa_nada():
    p = vision.proponer([], [], CATALOGO)
    assert p["nombre_sugerido"] is None
    assert p["categoria_sugerida"] is None
    assert p["nivel"] == "baja"


@pytest.mark.parametrize("confianza, nivel", [(85.0, "alta"), (84.9, "media"), (60.0, "media"), (59.9, "baja")])
def test_umbrales_de_la_propuesta(confianza, nivel):
    assert vision.nivel_de_confianza(confianza) == nivel


def test_para_dynamo_convierte_floats():
    convertido = vision.para_dynamo({"a": 1.5, "b": [{"c": 2.25}], "d": "x", "e": 3})
    assert convertido == {"a": Decimal("1.5"), "b": [{"c": Decimal("2.25")}], "d": "x", "e": 3}


# --- Servicio con dobles en memoria ---------------------------------------------------


class RepoFalso:
    def __init__(self):
        self.items: dict[str, dict] = {}

    def crear(self, item):
        self.items[item["identificacion_id"]] = dict(item)
        return item

    def obtener(self, iid):
        if iid not in self.items:
            raise ErrorNoEncontrado("no existe")
        return dict(self.items[iid])

    def completar(self, iid, propuesta):
        self.items[iid].update(estado="lista", propuesta=propuesta)

    def fallar(self, iid, motivo):
        self.items[iid].update(estado="error", motivo=motivo)


class FotosFalsas:
    def url_subida(self, clave):
        return {"url": "https://bucket.s3.amazonaws.com/", "campos": {"key": clave}}


class ReconocimientoFalso:
    def __init__(self, falla=False):
        self.falla = falla

    def analizar(self, clave):
        if self.falla:
            raise RuntimeError("Rekognition no respondio")
        return [etiqueta("Wrench", 93.0)], []


class CategoriasFalsas:
    def listar(self, limite, cursor):
        return [{"categoria_id": c} for c in CATALOGO], None


def _servicio(falla=False):
    repo = RepoFalso()
    return repo, ServicioIdentificacion(repo, FotosFalsas(), ReconocimientoFalso(falla), CategoriasFalsas())


def test_flujo_completo():
    repo, servicio = _servicio()

    solicitud = servicio.solicitar("usuario-1")
    iid = solicitud["identificacion_id"]
    assert solicitud["subida"]["campos"]["key"] == f"fotos/{iid}.jpg"
    assert servicio.obtener(iid, "usuario-1")["estado"] == "pendiente"

    assert servicio.procesar(f"fotos/{iid}.jpg") == iid

    resultado = servicio.obtener(iid, "usuario-1")
    assert resultado["estado"] == "lista"
    assert resultado["propuesta"]["nombre_sugerido"] == "Llave"
    assert resultado["propuesta"]["categoria_sugerida"] == "herramientas"
    # Lo interno no sale por la API.
    assert {"solicitada_por", "clave_foto", "expira_en"}.isdisjoint(resultado)


def test_la_solicitud_expira_con_la_foto():
    repo, servicio = _servicio()
    iid = servicio.solicitar("u")["identificacion_id"]
    import time

    dias = (repo.items[iid]["expira_en"] - time.time()) / 86400
    assert 29.9 < dias <= 30


def test_otro_usuario_no_ve_la_identificacion():
    _, servicio = _servicio()
    iid = servicio.solicitar("usuario-1")["identificacion_id"]
    with pytest.raises(ErrorNoEncontrado):
        servicio.obtener(iid, "usuario-2")


@pytest.mark.parametrize(
    "clave",
    ["fotos/no-es-uuid.jpg", "otra/123e4567-e89b-12d3-a456-426614174000.jpg", "fotos/../secreto.jpg", ""],
)
def test_claves_ajenas_se_ignoran(clave):
    _, servicio = _servicio()
    assert servicio.procesar(clave) is None


def test_si_rekognition_falla_queda_registrado_el_error():
    repo, servicio = _servicio(falla=True)
    iid = servicio.solicitar("u")["identificacion_id"]
    with pytest.raises(RuntimeError):
        servicio.procesar(f"fotos/{iid}.jpg")
    assert repo.items[iid]["estado"] == "error"


# --- Adaptadores de AWS ---------------------------------------------------------------


@pytest.fixture()
def credenciales(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "prueba")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "prueba")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


def test_url_de_subida_limita_tipo_y_tamano(credenciales):
    import base64
    import json

    from localizador.vision_aws import TAMANO_MAXIMO_FOTO, AlmacenFotosS3

    subida = AlmacenFotosS3("bucket-fotos").url_subida("fotos/abc.jpg")

    politica = json.loads(base64.b64decode(subida["campos"]["policy"]))
    condiciones = politica["conditions"]
    assert {"Content-Type": "image/jpeg"} in condiciones
    assert ["content-length-range", 1, TAMANO_MAXIMO_FOTO] in condiciones
    assert subida["campos"]["key"] == "fotos/abc.jpg"


def test_rekognition_lee_la_foto_desde_s3(credenciales):
    import boto3

    from localizador.vision_aws import ReconocimientoRekognition

    cliente = boto3.client("rekognition")
    stub = Stubber(cliente)
    imagen = {"S3Object": {"Bucket": "bucket-fotos", "Name": "fotos/abc.jpg"}}
    stub.add_response(
        "detect_labels",
        {"Labels": [{"Name": "Drill", "Confidence": 97.0}]},
        {"Image": imagen, "MaxLabels": 15, "MinConfidence": 55.0},
    )
    stub.add_response("detect_text", {"TextDetections": []}, {"Image": imagen})
    stub.activate()

    etiquetas, textos = ReconocimientoRekognition("bucket-fotos", cliente).analizar("fotos/abc.jpg")

    stub.assert_no_pending_responses()
    assert etiquetas[0]["Name"] == "Drill" and textos == []


def test_lambda_del_evento_de_s3(monkeypatch):
    ruta = RAIZ / "src" / "identificar_objeto" / "app.py"
    spec = importlib.util.spec_from_file_location("lambda_identificar", ruta)
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)

    repo, servicio = _servicio()
    iid = servicio.solicitar("u")["identificacion_id"]
    monkeypatch.setattr(app, "_servicio", servicio)

    evento = {
        "Records": [
            {"s3": {"object": {"key": f"fotos/{iid}.jpg"}}},
            {"s3": {"object": {"key": "subida+a+mano.jpg"}}},
        ]
    }
    assert app.lambda_handler(evento, None) == {"procesadas": [iid]}
    assert repo.items[iid]["estado"] == "lista"
