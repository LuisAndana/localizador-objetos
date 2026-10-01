"""Pruebas de extremo a extremo del servidor local (FastAPI + SQLite + simulador)."""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZADOR_BD", str(tmp_path / "prueba.db"))
    import main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


NUEVO = {
    "object_id": "obj-prueba-1",
    "nombre": "Martillo de bola",
    "categoria": "herramientas",
    "almacen_id": "almacen-01",
    "pasillo": "A",
    "anaquel": "2",
    "nivel": "1",
    "posicion_led": 30,
}


def test_salud_y_semilla(cliente):
    assert cliente.get("/api/salud").json()["modo"] == "local"
    categorias = cliente.get("/api/categorias").json()["elementos"]
    assert {c["categoria_id"] for c in categorias} >= {"herramientas", "refacciones"}


def test_listar_por_categoria_ordenado_por_nombre(cliente):
    r = cliente.get("/api/objetos", params={"categoria": "herramientas"})
    assert r.status_code == 200
    nombres = [o["nombre"] for o in r.json()["elementos"]]
    assert nombres == sorted(nombres) and len(nombres) == 3


def test_paginacion_por_cursor_recorre_todo_sin_repetir(cliente):
    vistos, cursor = [], None
    while True:
        params = {"limite": "5", **({"cursor": cursor} if cursor else {})}
        cuerpo = cliente.get("/api/objetos", params=params).json()
        vistos += [o["object_id"] for o in cuerpo["elementos"]]
        cursor = cuerpo["siguiente_cursor"]
        if not cursor:
            break
    assert len(vistos) == len(set(vistos)) == 12


def test_cursor_de_otra_consulta_es_400(cliente):
    cursor = cliente.get("/api/objetos", params={"limite": "2"}).json()["siguiente_cursor"]
    r = cliente.get("/api/objetos", params={"categoria": "herramientas", "cursor": cursor})
    assert r.status_code == 400


def test_crear_obtener_y_conflicto(cliente):
    r = cliente.post("/api/objetos", json=NUEVO)
    assert r.status_code == 201
    assert r.json()["color_indicador"] == "#00FF00"
    assert cliente.get("/api/objetos/obj-prueba-1").json()["nombre"] == "Martillo de bola"
    assert cliente.post("/api/objetos", json=NUEVO).status_code == 409


def test_no_se_puede_repetir_la_posicion_del_led_en_un_almacen(cliente):
    # La semilla ya tiene un objeto en el LED 42 del almacen-01.
    ocupado = cliente.get("/api/objetos/obj-demo-001").json()
    repetido = {**NUEVO, "object_id": "obj-choque", "posicion_led": ocupado["posicion_led"]}

    r = cliente.post("/api/objetos", json=repetido)
    assert r.status_code == 409
    assert r.json()["detalles"]["campo"] == "posicion_led"

    # La misma posicion en otro almacen si es valida: cada uno tiene su tira.
    otro_almacen = {**repetido, "almacen_id": "almacen-02"}
    assert cliente.post("/api/objetos", json=otro_almacen).status_code == 201

    # Y editar un objeto sin mover su LED no choca consigo mismo.
    assert cliente.put("/api/objetos/obj-demo-001", json={"nivel": "4"}).status_code == 200
    assert (
        cliente.put(
            "/api/objetos/obj-demo-002", json={"posicion_led": ocupado["posicion_led"]}
        ).status_code
        == 409
    )


def test_crear_invalido_devuelve_campos(cliente):
    r = cliente.post("/api/objetos", json={"nombre": "Incompleto"})
    assert r.status_code == 400
    assert "posicion_led" in r.json()["detalles"]["campos"]


def test_actualizar_ubicacion_y_404(cliente):
    r = cliente.put("/api/objetos/obj-demo-001", json={"pasillo": "Z", "posicion_led": 5})
    assert r.status_code == 200
    assert (r.json()["pasillo"], r.json()["posicion_led"]) == ("Z", 5)
    assert cliente.put("/api/objetos/no-existe", json={"pasillo": "Z"}).status_code == 404
    assert cliente.put("/api/objetos/obj-demo-001", json={"object_id": "x"}).status_code == 400


def test_localizar_enciende_el_led_en_el_simulador(cliente):
    r = cliente.post("/api/objetos/obj-demo-001/localizar", json={"duracion_segundos": 20})
    assert r.status_code == 202
    assert r.json()["topic"] == "almacen/almacen-01/led"

    tira = cliente.get("/api/simulador/almacenes/almacen-01/led").json()
    activo = next(a for a in tira["activos"] if a["posicion_led"] == 42)
    assert activo["nombre"] == "Taladro percutor"
    assert 0 < activo["segundos_restantes"] <= 20
    assert tira["total_leds"] >= 120


def test_localizar_inexistente_es_404(cliente):
    assert cliente.post("/api/objetos/no-existe/localizar").status_code == 404


def test_simulador_rechaza_inyeccion_de_topic(cliente):
    assert cliente.get("/api/simulador/almacenes/almacen%2B/led").status_code == 400


def test_ruta_api_desconocida_es_404_json(cliente):
    r = cliente.get("/api/no-existe")
    assert r.status_code == 404 and r.json()["error"] == "no_encontrado"
