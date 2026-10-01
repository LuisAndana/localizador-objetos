"""Pruebas de entradas y salidas: POST /movimientos y GET /movimientos."""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

OBJETO = "obj-demo-001"  # Taladro percutor, 2 piezas en la semilla


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZADOR_BD", str(tmp_path / "prueba.db"))
    import main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def _cantidad(cliente, object_id: str = OBJETO) -> int:
    return cliente.get(f"/api/objetos/{object_id}").json()["cantidad"]


def test_entrada_suma_y_salida_resta(cliente):
    assert _cantidad(cliente) == 2

    r = cliente.post("/api/movimientos", json={"object_id": OBJETO, "tipo": "entrada", "cantidad": 5})
    assert r.status_code == 201
    assert r.json()["objeto"]["cantidad"] == 7
    assert r.json()["movimiento"]["origen"] == "app"

    r = cliente.post("/api/movimientos", json={"object_id": OBJETO, "tipo": "salida", "cantidad": 3})
    assert r.status_code == 201
    assert r.json()["objeto"]["cantidad"] == 4
    assert _cantidad(cliente) == 4


def test_salida_mayor_que_las_existencias_es_409_y_no_mueve_nada(cliente):
    r = cliente.post("/api/movimientos", json={"object_id": OBJETO, "tipo": "salida", "cantidad": 99})

    assert r.status_code == 409
    assert _cantidad(cliente) == 2, "una salida rechazada no debe tocar la cantidad"
    assert cliente.get("/api/movimientos", params={"object_id": OBJETO}).json()["elementos"] == []


def test_movimiento_sobre_objeto_inexistente_es_404(cliente):
    r = cliente.post("/api/movimientos", json={"object_id": "obj-fantasma", "tipo": "entrada", "cantidad": 1})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"object_id": OBJETO, "tipo": "prestamo", "cantidad": 1},
        {"object_id": OBJETO, "tipo": "salida", "cantidad": 0},
        {"object_id": OBJETO, "tipo": "salida", "cantidad": -2},
        {"object_id": OBJETO, "tipo": "entrada", "cantidad": "tres"},
        {"object_id": OBJETO, "cantidad": 1},
        {"object_id": OBJETO, "tipo": "entrada", "cantidad": 1, "origen": "robot"},
    ],
)
def test_cuerpos_invalidos_son_400(cliente, cuerpo):
    assert cliente.post("/api/movimientos", json=cuerpo).status_code == 400


def test_historial_va_del_mas_reciente_al_mas_viejo(cliente):
    for cantidad in (1, 2, 3):
        cliente.post(
            "/api/movimientos",
            json={"object_id": OBJETO, "tipo": "entrada", "cantidad": cantidad, "motivo": f"lote {cantidad}"},
        )

    elementos = cliente.get("/api/movimientos", params={"object_id": OBJETO}).json()["elementos"]

    assert [m["cantidad"] for m in elementos] == [3, 2, 1]
    assert elementos[0]["motivo"] == "lote 3"


def test_historial_pagina_sin_repetir(cliente):
    for _ in range(5):
        cliente.post("/api/movimientos", json={"object_id": OBJETO, "tipo": "entrada", "cantidad": 1})

    vistos, cursor = [], None
    while True:
        params = {"object_id": OBJETO, "limite": "2", **({"cursor": cursor} if cursor else {})}
        cuerpo = cliente.get("/api/movimientos", params=params).json()
        vistos += [m["movimiento_id"] for m in cuerpo["elementos"]]
        cursor = cuerpo["siguiente_cursor"]
        if not cursor:
            break

    assert len(vistos) == len(set(vistos)) == 5


def test_historial_sin_object_id_es_400(cliente):
    assert cliente.get("/api/movimientos").status_code == 400


def test_objeto_nuevo_nace_sin_existencias(cliente):
    cliente.post(
        "/api/objetos",
        json={
            "object_id": "obj-mov-1",
            "nombre": "Cinta de teflon",
            "categoria": "consumibles",
            "almacen_id": "almacen-01",
            "pasillo": "B",
            "anaquel": "1",
            "nivel": "1",
            "posicion_led": 70,
        },
    )
    assert _cantidad(cliente, "obj-mov-1") == 0
    assert cliente.post(
        "/api/movimientos", json={"object_id": "obj-mov-1", "tipo": "salida", "cantidad": 1}
    ).status_code == 409
