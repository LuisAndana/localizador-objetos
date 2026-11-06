"""Registro restringido por dominio: Cognito PreSignUp."""

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _cargar():
    ruta = RAIZ / "src" / "validar_registro" / "app.py"
    spec = importlib.util.spec_from_file_location("validar_registro_app", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _evento(correo: str) -> dict:
    return {"request": {"userAttributes": {"email": correo}}, "response": {}}


@pytest.fixture()
def dominios(monkeypatch):
    monkeypatch.setenv("DOMINIOS_PERMITIDOS", "mamagui.com, almacen.mx")


@pytest.mark.parametrize("correo", ["ana@mamagui.com", "LUIS@Mamagui.com", "a.b+c@almacen.mx"])
def test_acepta_dominios_permitidos(dominios, correo):
    modulo = _cargar()
    respuesta = modulo.lambda_handler(_evento(correo), None)
    assert respuesta["response"]["autoConfirmUser"] is False
    assert respuesta["response"]["autoVerifyEmail"] is False


@pytest.mark.parametrize(
    "correo",
    [
        "intruso@gmail.com",
        "ana@mamagui.com.evil.net",
        "ana@sub.mamagui.com",
        "sin-arroba.mamagui.com",
        "ana@mamagui.com; DROP",
        "",
    ],
)
def test_rechaza_otros_dominios_y_formatos_invalidos(dominios, correo):
    modulo = _cargar()
    with pytest.raises(Exception, match="Registro no permitido"):
        modulo.lambda_handler(_evento(correo), None)


def test_sin_dominios_configurados_nadie_se_registra(monkeypatch):
    monkeypatch.setenv("DOMINIOS_PERMITIDOS", "")
    modulo = _cargar()
    with pytest.raises(Exception, match="Registro no permitido"):
        modulo.lambda_handler(_evento("ana@mamagui.com"), None)
