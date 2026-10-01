"""Pruebas de eliminar objetos, gestionar categorias y buscar por nombre en el servidor."""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

SIN_EXISTENCIAS = {
    "object_id": "obj-prueba-borrar",
    "nombre": "Escalera de tijera",
    "categoria": "herramientas",
    "almacen_id": "almacen-01",
    "pasillo": "A",
    "anaquel": "9",
    "nivel": "1",
    "posicion_led": 140,
}


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZADOR_BD", str(tmp_path / "prueba.db"))
    import main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


# --- Eliminar objetos -----------------------------------------------------------------


def test_eliminar_objeto_sin_existencias(cliente):
    assert cliente.post("/api/objetos", json=SIN_EXISTENCIAS).status_code == 201

    r = cliente.delete("/api/objetos/obj-prueba-borrar")

    assert r.status_code == 200
    assert r.json()["nombre"] == "Escalera de tijera"
    assert cliente.get("/api/objetos/obj-prueba-borrar").status_code == 404


def test_eliminar_libera_la_posicion_led(cliente):
    cliente.post("/api/objetos", json=SIN_EXISTENCIAS)
    cliente.delete("/api/objetos/obj-prueba-borrar")

    otro = {**SIN_EXISTENCIAS, "object_id": "obj-prueba-nuevo", "nombre": "Carretilla"}
    assert cliente.post("/api/objetos", json=otro).status_code == 201


def test_no_se_elimina_un_objeto_con_existencias(cliente):
    # El taladro de la semilla tiene 2 piezas.
    r = cliente.delete("/api/objetos/obj-demo-001")

    assert r.status_code == 409
    assert r.json()["detalles"]["cantidad"] == 2
    assert cliente.get("/api/objetos/obj-demo-001").status_code == 200


def test_tras_sacar_todo_ya_se_puede_eliminar(cliente):
    cliente.post("/api/movimientos", json={"object_id": "obj-demo-001", "tipo": "salida", "cantidad": 2})

    assert cliente.delete("/api/objetos/obj-demo-001").status_code == 200


def test_eliminar_inexistente_es_404(cliente):
    assert cliente.delete("/api/objetos/no-existe").status_code == 404


def test_eliminar_con_id_invalido_es_400(cliente):
    assert cliente.delete("/api/objetos/con espacio").status_code == 400


# --- Categorias -----------------------------------------------------------------------


def test_crear_categoria(cliente):
    r = cliente.post(
        "/api/categorias",
        json={"categoria_id": "seguridad", "nombre": "Seguridad", "descripcion": "Equipo de protección"},
    )

    assert r.status_code == 201
    ids = {c["categoria_id"] for c in cliente.get("/api/categorias").json()["elementos"]}
    assert "seguridad" in ids


def test_categoria_sin_descripcion_queda_vacia(cliente):
    r = cliente.post("/api/categorias", json={"categoria_id": "limpieza", "nombre": "Limpieza"})

    assert r.status_code == 201
    assert r.json()["descripcion"] == ""


def test_categoria_duplicada_es_409(cliente):
    r = cliente.post("/api/categorias", json={"categoria_id": "herramientas", "nombre": "Otra"})
    assert r.status_code == 409


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"nombre": "Sin id"},
        {"categoria_id": "con espacio", "nombre": "X"},
        {"categoria_id": "ok", "nombre": ""},
        {"categoria_id": "ok", "nombre": "X", "color": "rojo"},
    ],
)
def test_categoria_invalida_es_400(cliente, cuerpo):
    assert cliente.post("/api/categorias", json=cuerpo).status_code == 400


def test_actualizar_categoria(cliente):
    r = cliente.put("/api/categorias/herramientas", json={"nombre": "Herramienta", "descripcion": "Nueva"})

    assert r.status_code == 200
    assert r.json() == {"categoria_id": "herramientas", "nombre": "Herramienta", "descripcion": "Nueva"}


def test_el_id_de_categoria_no_se_cambia(cliente):
    r = cliente.put("/api/categorias/herramientas", json={"categoria_id": "otra"})
    assert r.status_code == 400


def test_actualizar_categoria_inexistente_es_404(cliente):
    assert cliente.put("/api/categorias/no-existe", json={"nombre": "X"}).status_code == 404


def test_no_se_elimina_una_categoria_con_objetos(cliente):
    r = cliente.delete("/api/categorias/herramientas")

    assert r.status_code == 409
    ids = {c["categoria_id"] for c in cliente.get("/api/categorias").json()["elementos"]}
    assert "herramientas" in ids


def test_eliminar_categoria_vacia(cliente):
    cliente.post("/api/categorias", json={"categoria_id": "temporal", "nombre": "Temporal"})

    assert cliente.delete("/api/categorias/temporal").status_code == 200
    assert cliente.delete("/api/categorias/temporal").status_code == 404


def test_no_se_registra_un_objeto_con_categoria_inexistente(cliente):
    r = cliente.post("/api/objetos", json={**SIN_EXISTENCIAS, "categoria": "inventada"})

    assert r.status_code == 400
    assert r.json()["detalles"]["campo"] == "categoria"


def test_no_se_mueve_un_objeto_a_una_categoria_inexistente(cliente):
    r = cliente.put("/api/objetos/obj-demo-001", json={"categoria": "inventada"})
    assert r.status_code == 400


# --- Busqueda por nombre en el servidor -----------------------------------------------


def _nombres(cliente, **params) -> list[str]:
    r = cliente.get("/api/objetos", params=params)
    assert r.status_code == 200, r.text
    return [o["nombre"] for o in r.json()["elementos"]]


def test_busca_en_todo_el_catalogo_sin_importar_la_pagina(cliente):
    # Con limite 5 la primera pagina normal no trae el multimetro; la busqueda si.
    assert "Multímetro digital" not in _nombres(cliente, limite="5")
    assert _nombres(cliente, q="multi", limite="5") == ["Multímetro digital"]


def test_busqueda_ignora_acentos_y_mayusculas(cliente):
    assert _nombres(cliente, q="MULTIMETRO") == ["Multímetro digital"]
    assert _nombres(cliente, q="transmision") == ["Banda de transmisión"]


def test_busqueda_por_codigo(cliente):
    assert _nombres(cliente, q="obj-demo-004") == ["Rodamiento 6204"]


def test_busqueda_dentro_de_una_categoria(cliente):
    assert _nombres(cliente, q="torque", categoria="herramientas") == ["Llave de torque"]
    assert _nombres(cliente, q="torque", categoria="refacciones") == []


def test_busqueda_sin_resultados(cliente):
    assert _nombres(cliente, q="no-existe-nada") == []


def test_los_comodines_se_buscan_literalmente(cliente):
    # '%' en LIKE significaria "cualquier cosa": aqui debe buscarse el caracter.
    assert _nombres(cliente, q="%%") == []


def test_busqueda_de_un_caracter_es_400(cliente):
    assert cliente.get("/api/objetos", params={"q": "a"}).status_code == 400


def test_busqueda_vacia_lista_normal(cliente):
    assert len(_nombres(cliente, q="   ")) == 12


def test_busqueda_paginada_no_repite(cliente):
    vistos, cursor = [], None
    while True:
        params = {"q": "de", "limite": "2"}
        if cursor:
            params["cursor"] = cursor
        cuerpo = cliente.get("/api/objetos", params=params).json()
        vistos += [o["object_id"] for o in cuerpo["elementos"]]
        cursor = cuerpo["siguiente_cursor"]
        if not cursor:
            break
    assert len(vistos) == len(set(vistos)) >= 3


def test_el_nombre_editado_se_encuentra(cliente):
    cliente.put("/api/objetos/obj-demo-001", json={"nombre": "Rotomartillo"})

    assert _nombres(cliente, q="rotomart") == ["Rotomartillo"]
    assert _nombres(cliente, q="taladro") == []
