"""Pruebas del mapa 2D: GET /almacenes y GET /almacenes/{id}/plano."""

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


def _plano_pasillo(plano: dict, pasillo: str) -> dict:
    return next(p for p in plano["pasillos"] if p["pasillo"] == pasillo)


def _anaquel(plano: dict, pasillo: str, anaquel: str) -> dict:
    fila = _plano_pasillo(plano, pasillo)
    return next(a for a in fila["anaqueles"] if a["anaquel"] == anaquel)


def test_listar_almacenes_resume_objetos_y_pasillos(cliente):
    elementos = cliente.get("/api/almacenes").json()["elementos"]
    assert [a["almacen_id"] for a in elementos] == ["almacen-01", "almacen-02"]
    assert elementos[0] == {"almacen_id": "almacen-01", "total_objetos": 6, "total_pasillos": 2}
    assert elementos[1]["total_pasillos"] == 3


def test_plano_agrupa_por_pasillo_anaquel_y_nivel(cliente):
    plano = cliente.get("/api/almacenes/almacen-01/plano").json()

    assert plano["total_objetos"] == 6
    assert [p["pasillo"] for p in plano["pasillos"]] == ["A", "B"]
    assert [a["anaquel"] for a in _plano_pasillo(plano, "A")["anaqueles"]] == ["1", "3", "4"]

    nivel_2 = next(n for n in _anaquel(plano, "A", "3")["niveles"] if n["nivel"] == "2")
    assert [o["nombre"] for o in nivel_2["objetos"]] == ["Taladro percutor"]
    assert nivel_2["objetos"][0]["posicion_led"] == 42


def test_plano_incluye_los_niveles_vacios_del_anaquel(cliente):
    plano = cliente.get("/api/almacenes/almacen-01/plano").json()

    # El anaquel 5 del pasillo B solo tiene objetos en el nivel 4: el mapa debe
    # dibujar tambien los niveles 1 a 3, vacios, como en el anaquel real.
    anaquel = _anaquel(plano, "B", "5")
    assert [n["nivel"] for n in anaquel["niveles"]] == ["1", "2", "3", "4"]
    assert [len(n["objetos"]) for n in anaquel["niveles"]] == [0, 0, 0, 1]
    assert anaquel["total_objetos"] == 1


def test_objeto_recien_creado_aparece_en_el_plano(cliente):
    cliente.post(
        "/api/objetos",
        json={
            "object_id": "obj-plano-1",
            "nombre": "Escuadra metalica",
            "categoria": "herramientas",
            "almacen_id": "almacen-01",
            "pasillo": "A",
            "anaquel": "3",
            "nivel": "1",
            "posicion_led": 40,
        },
    )

    plano = cliente.get("/api/almacenes/almacen-01/plano").json()
    nivel_1 = next(n for n in _anaquel(plano, "A", "3")["niveles"] if n["nivel"] == "1")

    assert [o["object_id"] for o in nivel_1["objetos"]] == ["obj-plano-1"]
    assert plano["total_objetos"] == 7


def test_almacen_sin_objetos_es_404(cliente):
    r = cliente.get("/api/almacenes/almacen-99/plano")
    assert r.status_code == 404
    assert r.json()["error"] == "no_encontrado"


def test_almacen_id_invalido_es_400(cliente):
    assert cliente.get("/api/almacenes/almacen 01/plano").status_code == 400
