"""Repositorios de DynamoDB (los que usan las Lambdas) contra respuestas simuladas.

No hace falta cuenta de AWS: el Stubber de botocore intercepta cada llamada antes
de que salga a la red y devuelve la respuesta que se le indica.
"""

import pytest
from botocore.stub import ANY, Stubber

from localizador import repositorios
from localizador.errores import ErrorConflicto, ErrorNoEncontrado


@pytest.fixture(autouse=True)
def credenciales_falsas(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "prueba")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "prueba")
    monkeypatch.setattr(repositorios, "_recurso", None)


def _stub(repo):
    stub = Stubber(repo._tabla.meta.client)
    stub.activate()
    return stub


def _objeto(object_id: str, nombre: str, cantidad: int = 0) -> dict:
    return {
        "object_id": {"S": object_id},
        "nombre": {"S": nombre},
        "nombre_busqueda": {"S": nombre.lower()},
        "cantidad": {"N": str(cantidad)},
    }


def test_crear_guarda_el_nombre_normalizado_y_no_lo_devuelve():
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    # El Stubber ve los parametros antes de que boto3 los pase al formato de DynamoDB.
    guardado = {
        "object_id": "o1",
        "nombre": "Multímetro Digital",
        "nombre_busqueda": "multimetro digital",
        "ultima_actualizacion": ANY,
    }
    stub.add_response(
        "put_item", {}, {"TableName": "Objetos", "Item": guardado, "ConditionExpression": ANY}
    )

    item = repo.crear({"object_id": "o1", "nombre": "Multímetro Digital"})

    stub.assert_no_pending_responses()
    assert "nombre_busqueda" not in item
    assert item["nombre"] == "Multímetro Digital"


def test_eliminar_con_existencias_es_conflicto():
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    stub.add_client_error("delete_item", service_error_code="ConditionalCheckFailedException")
    stub.add_response("get_item", {"Item": _objeto("o1", "Taladro", cantidad=3)})

    with pytest.raises(ErrorConflicto) as error:
        repo.eliminar("o1")
    assert error.value.detalles == {"cantidad": 3}


def test_eliminar_inexistente_es_404():
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    stub.add_client_error("delete_item", service_error_code="ConditionalCheckFailedException")
    stub.add_response("get_item", {})

    with pytest.raises(ErrorNoEncontrado):
        repo.eliminar("o1")


def test_eliminar_devuelve_lo_borrado_sin_campos_internos():
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    stub.add_response("delete_item", {"Attributes": _objeto("o1", "Taladro")})

    borrado = repo.eliminar("o1")

    assert borrado["object_id"] == "o1" and "nombre_busqueda" not in borrado


def test_buscar_sigue_leyendo_paginas_hasta_juntar_el_limite():
    """El filtro se aplica despues de leer: una pagina puede traer 0 coincidencias."""
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    stub.add_response("scan", {"Items": [], "LastEvaluatedKey": {"object_id": {"S": "a"}}})
    stub.add_response(
        "scan",
        {"Items": [_objeto("o2", "Llave"), _objeto("o3", "Llave inglesa")], "LastEvaluatedKey": {"object_id": {"S": "b"}}},
    )

    items, cursor = repo.buscar("llave", None, limite=2)

    stub.assert_no_pending_responses()
    assert [i["object_id"] for i in items] == ["o2", "o3"]
    assert cursor == {"object_id": "b"}
    assert all("nombre_busqueda" not in i for i in items)


def test_buscar_con_categoria_usa_el_indice():
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    stub.add_response(
        "query",
        {"Items": [_objeto("o2", "Llave")]},
        {
            "TableName": "Objetos",
            "IndexName": "categoria-index",
            "KeyConditionExpression": ANY,
            "FilterExpression": ANY,
            "Limit": ANY,
        },
    )

    items, cursor = repo.buscar("llave", "herramientas", limite=10)

    stub.assert_no_pending_responses()
    assert len(items) == 1 and cursor is None


def test_hay_en_categoria():
    repo = repositorios.RepositorioObjetos("Objetos", "categoria-index")
    stub = _stub(repo)
    stub.add_response("query", {"Items": [{"object_id": {"S": "o1"}}]})
    stub.add_response("query", {"Items": []})

    assert repo.hay_en_categoria("herramientas") is True
    assert repo.hay_en_categoria("vacia") is False


def test_categoria_duplicada_es_conflicto():
    repo = repositorios.RepositorioCategorias("Categorias")
    stub = _stub(repo)
    stub.add_client_error("put_item", service_error_code="ConditionalCheckFailedException")

    with pytest.raises(ErrorConflicto):
        repo.crear({"categoria_id": "herramientas", "nombre": "X", "descripcion": ""})


def test_actualizar_categoria_inexistente_es_404():
    repo = repositorios.RepositorioCategorias("Categorias")
    stub = _stub(repo)
    stub.add_client_error("update_item", service_error_code="ConditionalCheckFailedException")

    with pytest.raises(ErrorNoEncontrado):
        repo.actualizar("no-existe", {"nombre": "X"})


def test_existe_categoria():
    repo = repositorios.RepositorioCategorias("Categorias")
    stub = _stub(repo)
    stub.add_response("get_item", {"Item": {"categoria_id": {"S": "herramientas"}}})
    stub.add_response("get_item", {})

    assert repo.existe("herramientas") is True
    assert repo.existe("otra") is False
