"""Quien puede hacer que: grupos de Cognito y su efecto en las Lambdas."""

import importlib.util
import json
from pathlib import Path

import pytest

from localizador import autorizacion, config
from localizador.errores import ErrorProhibido

RAIZ = Path(__file__).resolve().parents[1]


def _evento(grupos=None, **extra) -> dict:
    claims = {"sub": "usuario-1"}
    if grupos is not None:
        claims["cognito:groups"] = grupos
    return {"requestContext": {"authorizer": {"claims": claims}}, **extra}


@pytest.fixture()
def autenticacion(monkeypatch):
    monkeypatch.setenv("AUTENTICACION_ACTIVA", "true")
    config.autenticacion_activa.cache_clear()
    yield
    config.autenticacion_activa.cache_clear()


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("administradores", {"administradores"}),
        ("[administradores operadores]", {"administradores", "operadores"}),
        ("administradores,operadores", {"administradores", "operadores"}),
        (["administradores"], {"administradores"}),
        ("", set()),
    ],
)
def test_lee_los_grupos_en_todos_los_formatos(bruto, esperado):
    assert autorizacion.grupos(_evento(bruto)) == esperado


def test_sin_claims_no_hay_grupos():
    assert autorizacion.grupos({}) == set()


def test_administrador_pasa(autenticacion):
    autorizacion.exigir_administrador(_evento("administradores"))


def test_operador_no_pasa(autenticacion):
    with pytest.raises(ErrorProhibido):
        autorizacion.exigir_administrador(_evento("operadores"))


def test_usuario_sin_grupo_no_pasa(autenticacion):
    with pytest.raises(ErrorProhibido):
        autorizacion.exigir_administrador(_evento())


def test_un_grupo_que_solo_contiene_el_nombre_no_pasa(autenticacion):
    with pytest.raises(ErrorProhibido):
        autorizacion.exigir_administrador(_evento("no-administradores"))


def test_sin_autenticacion_activa_no_se_exige(monkeypatch):
    monkeypatch.delenv("AUTENTICACION_ACTIVA", raising=False)
    config.autenticacion_activa.cache_clear()
    autorizacion.exigir_administrador(_evento("operadores"))


def _cargar_lambda(nombre: str):
    ruta = RAIZ / "src" / nombre / "app.py"
    spec = importlib.util.spec_from_file_location(f"lambda_{nombre}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize(
    "nombre, ruta",
    [
        ("eliminar_objeto", {"object_id": "obj-1"}),
        ("crear_categoria", None),
        ("actualizar_categoria", {"categoria_id": "herramientas"}),
        ("eliminar_categoria", {"categoria_id": "herramientas"}),
    ],
)
def test_las_lambdas_de_administracion_responden_403_a_un_operador(autenticacion, nombre, ruta):
    """El 403 sale antes de tocar DynamoDB: no hace falta simular la base."""
    app = _cargar_lambda(nombre)
    evento = _evento("operadores", pathParameters=ruta, body=json.dumps({"nombre": "X"}))

    r = app.lambda_handler(evento, None)

    assert r["statusCode"] == 403
    assert json.loads(r["body"])["error"] == "prohibido"
    assert "Authorization" in r["headers"]["Access-Control-Allow-Headers"]
