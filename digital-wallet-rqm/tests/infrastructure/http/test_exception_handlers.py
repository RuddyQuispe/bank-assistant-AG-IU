import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from digital_wallet_rqm.domain.errors import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
    SessionForbiddenError,
    UnauthorizedError,
)
from digital_wallet_rqm.infrastructure.http import exception_handlers as handlers
from digital_wallet_rqm.infrastructure.http.exception_handlers import register_exception_handlers


class _Body(BaseModel):
    question: str = Field(min_length=1)


def _client_raising(error: Exception) -> TestClient:
    # App mínima: un endpoint que lanza la excepción, con los handlers registrados como en create_app()
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise error

    @app.post("/validate")
    def validate(body: _Body) -> None:
        return None

    # raise_server_exceptions=False: se prueba la respuesta 500, no que el error se propague al test
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("error", "status", "title"),
    [
        (BadRequestError("Dato inválido"), 400, "Petición inválida"),
        (UnauthorizedError("Falta el token"), 401, "No autenticado"),
        (ForbiddenError("Prohibido"), 403, "Acceso denegado"),
        (NotFoundError("No existe la cuenta"), 404, "Recurso no encontrado"),
        (ConflictError("Ya existe"), 409, "Conflicto"),
    ],
)
def test_app_errors_map_to_status_with_error_and_detail(error: AppError, status: int, title: str) -> None:
    response = _client_raising(error).get("/boom")

    assert response.status_code == status
    assert response.json() == {"error": title, "detail": error.detail}


def test_error_without_detail_uses_its_default_detail() -> None:
    response = _client_raising(NotFoundError()).get("/boom")

    assert response.json() == {"error": "Recurso no encontrado", "detail": "El recurso pedido no existe"}


def test_subclasses_use_the_status_and_error_of_their_parent() -> None:
    response = _client_raising(SessionForbiddenError()).get("/boom")

    assert response.status_code == 403
    assert response.json() == {"error": "Acceso denegado", "detail": "La sesión pertenece a otro usuario"}


def test_unauthorized_adds_bearer_challenge_header() -> None:
    response = _client_raising(UnauthorizedError("Falta el token")).get("/boom")

    assert response.headers["www-authenticate"] == "Bearer"


def test_failed_login_is_401_without_bearer_challenge() -> None:
    response = _client_raising(InvalidCredentialsError()).get("/boom")

    assert response.status_code == 401
    assert response.json() == {"error": "No autenticado", "detail": "Usuario desconocido"}
    assert "www-authenticate" not in response.headers


def test_invalid_token_hides_the_internal_reason() -> None:
    response = _client_raising(InvalidTokenError("Signature has expired")).get("/boom")

    assert response.status_code == 401
    assert response.json() == {"error": "No autenticado", "detail": "Token inválido"}


def test_validation_error_is_422_with_error_and_detail() -> None:
    response = _client_raising(RuntimeError()).post("/validate", json={"question": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "Datos inválidos"
    assert body["detail"].startswith("body.question: ")


def test_unknown_route_is_404_with_error_and_detail() -> None:
    response = _client_raising(RuntimeError()).get("/no-existe")

    assert response.status_code == 404
    assert response.json() == {"error": "Recurso no encontrado", "detail": "Not Found"}


def test_app_error_without_specific_type_is_a_500() -> None:
    response = _client_raising(AppError("detalle interno")).get("/boom")

    assert response.status_code == 500
    assert response.json() == {"error": "Error interno del servidor", "detail": handlers.INTERNAL_ERROR_DETAIL}


def test_unexpected_exception_hides_traceback_by_default(caplog: pytest.LogCaptureFixture) -> None:
    response = _client_raising(RuntimeError("password=secreto")).get("/boom")

    assert response.status_code == 500
    assert response.json() == {"error": "Error interno del servidor", "detail": handlers.INTERNAL_ERROR_DETAIL}
    assert "secreto" not in response.text
    # El traceback real siempre queda en el log del servidor
    assert "password=secreto" in caplog.text


def test_unexpected_exception_sends_traceback_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handlers.settings, "ERROR_TRACEBACK_ENABLED", True)

    response = _client_raising(RuntimeError("falla de prueba")).get("/boom")

    body = response.json()
    assert body["error"] == "Error interno del servidor"
    assert body["detail"].startswith("Traceback (most recent call last)")
    assert "RuntimeError: falla de prueba" in body["detail"]
