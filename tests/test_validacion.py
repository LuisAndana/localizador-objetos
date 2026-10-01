import json

import pytest
from localizador import paginacion, validacion
from localizador.errores import ErrorValidacion

OBJETO_VALIDO = {
    "nombre": "Taladro percutor",
    "categoria": "herramientas",
    "almacen_id": "almacen-01",
    "pasillo": "A",
    "anaquel": "3",
    "nivel": "2",
    "posicion_led": 42,
}


def test_objeto_nuevo_aplica_color_por_defecto():
    limpio = validacion.objeto_nuevo(dict(OBJETO_VALIDO))
    assert limpio["color_indicador"] == validacion.COLOR_POR_DEFECTO
    assert limpio["posicion_led"] == 42


def test_objeto_nuevo_reporta_todos_los_campos_faltantes():
    with pytest.raises(ErrorValidacion) as exc:
        validacion.objeto_nuevo({"nombre": "Solo el nombre"})
    assert "categoria" in exc.value.detalles["campos"]
    assert "posicion_led" in exc.value.detalles["campos"]


@pytest.mark.parametrize(
    "almacen_id",
    ["almacen/01", "almacen-01/#", "+", "#", "../otro", "almacen 01", ""],
)
def test_almacen_id_rechaza_caracteres_de_topic_mqtt(almacen_id):
    """Un '/', '#' o '+' colado aqui permitiria publicar en topics ajenos."""
    datos = dict(OBJETO_VALIDO, almacen_id=almacen_id)
    with pytest.raises(ErrorValidacion):
        validacion.objeto_nuevo(datos)


def test_posicion_led_rechaza_booleanos():
    """True es instancia de int en Python: sin guardia pasaria como LED 1."""
    with pytest.raises(ErrorValidacion):
        validacion.objeto_nuevo(dict(OBJETO_VALIDO, posicion_led=True))


@pytest.mark.parametrize("valor", [-1, 70000, "42", 4.5, None])
def test_posicion_led_rechaza_valores_fuera_de_rango_o_tipo(valor):
    with pytest.raises(ErrorValidacion):
        validacion.objeto_nuevo(dict(OBJETO_VALIDO, posicion_led=valor))


@pytest.mark.parametrize("color", ["verde", "#GGG", "#00FF0", "00FF00", "#00FF00AA"])
def test_color_indicador_exige_formato_hex(color):
    with pytest.raises(ErrorValidacion):
        validacion.objeto_nuevo(dict(OBJETO_VALIDO, color_indicador=color))


def test_actualizacion_rechaza_campos_no_permitidos():
    with pytest.raises(ErrorValidacion) as exc:
        validacion.objeto_actualizacion({"object_id": "otro", "pasillo": "B"})
    assert exc.value.detalles["campos"] == ["object_id"]


def test_actualizacion_vacia_es_invalida():
    with pytest.raises(ErrorValidacion):
        validacion.objeto_actualizacion({})


def test_cuerpo_json_rechaza_json_no_objeto():
    with pytest.raises(ErrorValidacion):
        validacion.cuerpo_json({"body": "[1, 2, 3]"})


def test_cuerpo_json_opcional_devuelve_vacio():
    assert validacion.cuerpo_json({"body": None}, obligatorio=False) == {}


def test_cuerpo_json_rechaza_cuerpo_gigante():
    enorme = json.dumps({"nombre": "x" * (validacion.LONGITUD_MAXIMA_CUERPO + 10)})
    with pytest.raises(ErrorValidacion):
        validacion.cuerpo_json({"body": enorme})


def test_duracion_usa_defecto_si_no_se_indica():
    assert validacion.duracion_localizacion({}) == 30


@pytest.mark.parametrize("duracion", [0, -3, 9999, "10"])
def test_duracion_fuera_de_rango_es_invalida(duracion):
    with pytest.raises(ErrorValidacion):
        validacion.duracion_localizacion({"duracion_segundos": duracion})


def test_cursor_ida_y_vuelta():
    clave = {"object_id": "obj-demo-001"}
    assert paginacion.decodificar_cursor(paginacion.codificar_cursor(clave)) == clave


@pytest.mark.parametrize("cursor", ["no-base64!!", "e30=", "bm8tanNvbg==", "x" * 3000])
def test_cursor_manipulado_es_rechazado(cursor):
    with pytest.raises(ErrorValidacion):
        paginacion.decodificar_cursor(cursor)
