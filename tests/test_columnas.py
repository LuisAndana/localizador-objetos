"""Columnas del anaquel: el dato, la cuadricula del plano y la migracion de bases viejas."""

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from localizador import plano

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

NUEVO = {
    "object_id": "obj-col-1",
    "nombre": "Pinzas de corte",
    "categoria": "herramientas",
    "almacen_id": "almacen-01",
    "pasillo": "A",
    "anaquel": "1",
    "nivel": "3",
    "posicion_led": 13,
}


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZADOR_BD", str(tmp_path / "prueba.db"))
    import main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def _anaquel(plano_json: dict, pasillo: str, anaquel: str) -> dict:
    fila = next(p for p in plano_json["pasillos"] if p["pasillo"] == pasillo)
    return next(a for a in fila["anaqueles"] if a["anaquel"] == anaquel)


# --- El dato -------------------------------------------------------------------------


def test_sin_columna_va_a_la_primera(cliente):
    r = cliente.post("/api/objetos", json=NUEVO)
    assert r.status_code == 201
    assert r.json()["columna"] == "A"


def test_la_columna_se_guarda_en_mayusculas(cliente):
    r = cliente.post("/api/objetos", json={**NUEVO, "columna": "c"})
    assert r.json()["columna"] == "C"
    assert cliente.get("/api/objetos/obj-col-1").json()["columna"] == "C"


@pytest.mark.parametrize("columna", ["", "ABCD", "A-1", 3, "A B"])
def test_columna_invalida_es_400(cliente, columna):
    r = cliente.post("/api/objetos", json={**NUEVO, "columna": columna})
    assert r.status_code == 400


def test_mover_de_columna(cliente):
    r = cliente.put("/api/objetos/obj-demo-003", json={"columna": "B"})
    assert r.status_code == 200
    assert r.json()["columna"] == "B"


def test_localizar_informa_la_columna(cliente):
    r = cliente.post("/api/objetos/obj-demo-003/localizar", json={"duracion_segundos": 5})
    ubicacion = r.json()["ubicacion"]
    assert ubicacion["columna"] == "A"
    assert "columna A" in ubicacion["descripcion"]


# --- La cuadricula del plano ----------------------------------------------------------


def test_el_anaquel_trae_sus_columnas_y_cada_nivel_sus_celdas(cliente):
    cliente.post("/api/objetos", json={**NUEVO, "columna": "C"})
    anaquel = _anaquel(cliente.get("/api/almacenes/almacen-01/plano").json(), "A", "1")

    assert anaquel["columnas"] == ["A", "B", "C"]
    nivel_3 = next(n for n in anaquel["niveles"] if n["nivel"] == "3")
    assert [c["columna"] for c in nivel_3["celdas"]] == ["A", "B", "C"]
    assert [o["nombre"] for o in nivel_3["celdas"][0]["objetos"]] == ["Juego de desarmadores"]
    assert nivel_3["celdas"][1]["objetos"] == []
    assert [o["nombre"] for o in nivel_3["celdas"][2]["objetos"]] == ["Pinzas de corte"]
    # Los niveles vacios tambien traen sus celdas, para dibujar la cuadricula completa.
    nivel_1 = next(n for n in anaquel["niveles"] if n["nivel"] == "1")
    assert len(nivel_1["celdas"]) == 3 and all(c["objetos"] == [] for c in nivel_1["celdas"])


def _objeto(columna, nivel="1", led=1):
    return {
        "object_id": f"o-{columna}-{nivel}-{led}", "nombre": "x", "categoria": "c",
        "pasillo": "A", "anaquel": "1", "nivel": nivel, "columna": columna, "posicion_led": led,
    }


@pytest.mark.parametrize(
    "usadas, esperadas",
    [
        (["A"], ["A", "B", "C"]),
        (["E"], ["A", "B", "C", "D", "E"]),
        (["2"], ["1", "2", "3"]),
        (["5"], ["1", "2", "3", "4", "5"]),
        (["A", "10"], ["10", "A"]),
    ],
)
def test_columnas_se_completan_hasta_la_ultima(usadas, esperadas):
    resultado = plano.construir("alm", [_objeto(c, led=i) for i, c in enumerate(usadas)])
    assert resultado["pasillos"][0]["anaqueles"][0]["columnas"] == esperadas


def test_objeto_sin_columna_queda_en_la_primera():
    item = {k: v for k, v in _objeto("A").items() if k != "columna"}
    anaquel = plano.construir("alm", [item])["pasillos"][0]["anaqueles"][0]
    assert anaquel["niveles"][0]["celdas"][0]["objetos"][0]["columna"] == "A"


def test_varios_objetos_en_la_misma_celda():
    anaquel = plano.construir("alm", [_objeto("B", led=5), _objeto("B", led=2)])["pasillos"][0]["anaqueles"][0]
    celda_b = anaquel["niveles"][0]["celdas"][1]
    assert [o["posicion_led"] for o in celda_b["objetos"]] == [2, 5]


# --- Migracion de una base creada antes de las columnas -------------------------------


def test_base_vieja_se_migra_repartiendo_por_led(tmp_path, monkeypatch):
    ruta = tmp_path / "vieja.db"
    with sqlite3.connect(ruta) as con:
        con.executescript(
            """CREATE TABLE objetos (
                object_id TEXT PRIMARY KEY, nombre TEXT NOT NULL, categoria TEXT NOT NULL,
                almacen_id TEXT NOT NULL, pasillo TEXT NOT NULL, anaquel TEXT NOT NULL,
                nivel TEXT NOT NULL, posicion_led INTEGER NOT NULL, color_indicador TEXT NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 0, ultima_actualizacion TEXT NOT NULL);
            INSERT INTO objetos VALUES
                ('a', 'Uno', 'herramientas', 'alm', 'A', '1', '1', 30, '#00FF00', 0, 'x'),
                ('b', 'Dos', 'herramientas', 'alm', 'A', '1', '1', 10, '#00FF00', 0, 'x'),
                ('c', 'Tres', 'herramientas', 'alm', 'A', '1', '2', 20, '#00FF00', 0, 'x');"""
        )
    monkeypatch.setenv("LOCALIZADOR_BD", str(ruta))
    import main

    importlib.reload(main)
    with TestClient(main.app) as c:
        columnas = {o["object_id"]: o["columna"] for o in c.get("/api/objetos").json()["elementos"]}

    # En el nivel 1, el LED 10 queda a la izquierda (A) y el 30 a su derecha (B).
    assert columnas == {"a": "B", "b": "A", "c": "A"}
