"""Pruebas del indicador de tiempo de localizacion (la meta del 40 % del acta)."""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "layers" / "common"))

from localizador import metricas  # noqa: E402

OBJETO = "obj-demo-001"


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALIZADOR_BD", str(tmp_path / "prueba.db"))
    import main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def _localizar(cliente, object_id: str = OBJETO) -> str:
    r = cliente.post(f"/api/objetos/{object_id}/localizar", json={"duracion_segundos": 15})
    assert r.status_code == 202
    return r.json()["busqueda_id"]


def _resumen(cliente) -> dict:
    return cliente.get("/api/metricas/localizacion").json()


def test_sin_mediciones_no_inventa_un_porcentaje(cliente):
    resumen = _resumen(cliente)
    assert resumen["con_sistema"]["muestras"] == 0
    assert resumen["reduccion_pct"] is None
    assert resumen["cumple_meta"] is None


def test_localizar_abre_el_cronometro_y_la_salida_lo_cierra(cliente):
    busqueda_id = _localizar(cliente)
    assert _resumen(cliente)["busquedas_abiertas"] == 1

    r = cliente.post("/api/movimientos", json={"object_id": OBJETO, "tipo": "salida", "cantidad": 1})
    assert r.status_code == 201

    cerrada = r.json()["busqueda"]
    assert cerrada["busqueda_id"] == busqueda_id
    assert cerrada["cerrada_por"] == "salida"

    resumen = _resumen(cliente)
    assert resumen["busquedas_abiertas"] == 0
    assert resumen["con_sistema"]["muestras"] == 1


def test_confirmacion_manual_cierra_una_sola_vez(cliente):
    busqueda_id = _localizar(cliente)

    r = cliente.post(f"/api/busquedas/{busqueda_id}/confirmar")
    assert r.status_code == 200
    assert r.json()["cerrada_por"] == "app"
    assert r.json()["duracion_ms"] >= 0

    assert cliente.post(f"/api/busquedas/{busqueda_id}/confirmar").status_code == 409
    assert cliente.post("/api/busquedas/no-existe/confirmar").status_code == 404


def test_una_entrada_no_cierra_el_cronometro(cliente):
    _localizar(cliente)
    r = cliente.post("/api/movimientos", json={"object_id": OBJETO, "tipo": "entrada", "cantidad": 1})

    assert "busqueda" not in r.json()
    assert _resumen(cliente)["busquedas_abiertas"] == 1


def test_reduccion_se_calcula_contra_las_mediciones_manuales(cliente):
    for duracion in (60_000, 40_000):
        r = cliente.post("/api/busquedas", json={"object_id": OBJETO, "duracion_ms": duracion})
        assert r.status_code == 201

    cliente.post(f"/api/busquedas/{_localizar(cliente)}/confirmar")

    resumen = _resumen(cliente)
    assert resumen["manual"]["muestras"] == 2
    assert resumen["manual"]["promedio_ms"] == 50_000
    assert resumen["con_sistema"]["muestras"] == 1
    # El sistema responde en milisegundos contra 50 s a mano: la meta del 40 % se cumple.
    assert resumen["reduccion_pct"] > 40
    assert resumen["cumple_meta"] is True


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"object_id": OBJETO},
        {"object_id": OBJETO, "duracion_ms": 0},
        {"object_id": OBJETO, "duracion_ms": -5},
        {"object_id": OBJETO, "duracion_ms": 10_000_000},
        {"object_id": OBJETO, "duracion_ms": 1000, "modo": "sistema"},
    ],
)
def test_mediciones_manuales_invalidas_son_400(cliente, cuerpo):
    assert cliente.post("/api/busquedas", json=cuerpo).status_code == 400


def test_resumen_calcula_mediana_y_p90():
    busquedas = [
        {"modo": "sistema", "confirmada_en": "x", "duracion_ms": ms}
        for ms in (1000, 2000, 3000, 4000, 100_000)
    ] + [{"modo": "sistema", "confirmada_en": "", "duracion_ms": 0}]

    resumen = metricas.resumir(busquedas)

    assert resumen["con_sistema"]["muestras"] == 5
    assert resumen["con_sistema"]["mediana_ms"] == 3000
    assert resumen["con_sistema"]["p90_ms"] == 100_000
    assert resumen["busquedas_abiertas"] == 1, "una busqueda sin confirmar no promedia"
