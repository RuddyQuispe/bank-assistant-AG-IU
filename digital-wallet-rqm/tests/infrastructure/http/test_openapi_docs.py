"""La documentación sale del código (code first); docs/openapi.yaml es una copia exportada."""

import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.infrastructure.http.main import app, create_app
from digital_wallet_rqm.infrastructure.http.openapi_export import OPENAPI_YAML_PATH, build_openapi_yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations() -> list[tuple[str, dict]]:
    operations = []
    for path, path_item in app.openapi()["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                operations.append((f"{method.upper()} {path}", operation))
    return operations


def test_scalar_page_is_served():
    response = TestClient(app).get("/scalar")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/openapi.json" in response.text


def test_every_operation_has_a_summary():
    for name, operation in _operations():
        assert operation.get("summary"), name


def test_every_operation_documents_the_401_response():
    for name, operation in _operations():
        assert "401" in operation["responses"], name


def test_protected_operations_require_the_bearer_token():
    for name, operation in _operations():
        if name == "POST /auth/token":
            assert "security" not in operation
        else:
            assert operation["security"] == [{"HTTPBearer": []}], name


def test_exported_yaml_is_up_to_date():
    # Si falla: uv run python scripts/export_openapi.py
    assert OPENAPI_YAML_PATH.read_text(encoding="utf-8") == build_openapi_yaml()


def test_docs_can_be_disabled_by_config(monkeypatch):
    monkeypatch.setattr(settings, "DOCS_ENABLED", False)
    client = TestClient(create_app())

    for path in ("/docs", "/redoc", "/openapi.json", settings.SCALAR_PATH):
        assert client.get(path).status_code == 404, path


def test_docs_paths_title_and_theme_come_from_config(monkeypatch):
    monkeypatch.setattr(settings, "API_TITLE", "Wallet de prueba")
    monkeypatch.setattr(settings, "SCALAR_PATH", "/referencia")
    monkeypatch.setattr(settings, "SCALAR_THEME", "moon")
    client = TestClient(create_app())

    scalar = client.get("/referencia")

    assert scalar.status_code == 200
    assert "Wallet de prueba" in scalar.text
    assert '"moon"' in scalar.text
    assert client.get("/openapi.json").json()["info"]["title"] == "Wallet de prueba"


def test_invalid_scalar_theme_fails_on_startup(monkeypatch):
    monkeypatch.setattr(settings, "SCALAR_THEME", "morado")

    with pytest.raises(ValueError, match="morado"):
        create_app()
