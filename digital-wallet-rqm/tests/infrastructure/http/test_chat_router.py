from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.application.ports.inbound.chat_service import ChatAnswer, ChatMessage, ChatService
from digital_wallet_rqm.domain.errors import SessionForbiddenError, SessionNotFoundError
from digital_wallet_rqm.domain.models.chat_session import ChatSession
from digital_wallet_rqm.domain.models.current_user import CurrentUser
from digital_wallet_rqm.infrastructure.http.dependencies import get_chat_service, get_current_user
from digital_wallet_rqm.infrastructure.http.main import app

CREATED = datetime(2026, 10, 26, 10, 0, tzinfo=UTC)
UPDATED = datetime(2026, 10, 26, 11, 30, tzinfo=UTC)


def _session(session_id: str, title: str | None) -> ChatSession:
    return ChatSession(session_id=session_id, user_id="1", title=title, created_at=CREATED, updated_at=UPDATED)


class FakeChatService(ChatService):
    """Servicio falso: evita llamar al LLM y a la base de datos; "ajena" es de otro usuario y "nope" no existe"""

    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.users: list[str] = []

    @staticmethod
    def _check(session_id: str | None) -> None:
        if session_id == "ajena":
            raise SessionForbiddenError()
        if session_id == "nope":
            raise SessionNotFoundError()

    async def create_session(self, user: CurrentUser) -> ChatSession:
        self.users.append(user.user_id)
        return _session("nueva", None)

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        self._check(session_id)
        return ChatAnswer(session_id=session_id or "new-session", response=f"eco: {question}")

    async def list_sessions(self, user: CurrentUser) -> list[ChatSession]:
        self.users.append(user.user_id)
        return [_session("s1", "¿Cuánto cuesta un SPEI?"), _session("s2", None)]

    async def get_history(self, user: CurrentUser, session_id: str) -> list[ChatMessage]:
        self._check(session_id)
        return [ChatMessage(role="human", content="hola"), ChatMessage(role="ai", content="eco: hola")]

    async def delete_session(self, user: CurrentUser, session_id: str) -> None:
        self._check(session_id)
        self.deleted.append(session_id)


@pytest.fixture
def fake_service() -> Iterator[FakeChatService]:
    service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="1", nickname="ruddy")
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_service: FakeChatService) -> TestClient:
    # Sin "with": no se ejecuta el lifespan, así no se abre la base ni Chroma
    return TestClient(app)


def test_post_chat_returns_answer(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "hola", "session_id": "s1"})

    assert response.status_code == 200
    assert response.json() == {"session_id": "s1", "response": "eco: hola"}


def test_post_chat_without_session_returns_new_session(client: TestClient) -> None:
    response = client.post("/chat", json={"question": "hola"})

    assert response.status_code == 200
    assert response.json()["session_id"] == "new-session"


def test_post_chat_rejects_empty_question(client: TestClient) -> None:
    response = client.post("/chat", json={"question": ""})

    assert response.status_code == 422


def test_get_sessions(client: TestClient, fake_service: FakeChatService) -> None:
    response = client.get("/chat/sessions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "session_id": "s1",
            "title": "¿Cuánto cuesta un SPEI?",
            "created_at": "2026-10-26T10:00:00Z",
            "updated_at": "2026-10-26T11:30:00Z",
        },
        {
            "session_id": "s2",
            "title": None,
            "created_at": "2026-10-26T10:00:00Z",
            "updated_at": "2026-10-26T11:30:00Z",
        },
    ]
    # Las sesiones se piden para el usuario del token
    assert fake_service.users == ["1"]


def test_create_session_returns_201_with_server_id(client: TestClient, fake_service: FakeChatService) -> None:
    response = client.post("/chat/sessions")

    assert response.status_code == 201
    assert response.json()["session_id"] == "nueva"
    assert response.json()["title"] is None
    assert fake_service.users == ["1"]


def test_get_history(client: TestClient) -> None:
    response = client.get("/chat/sessions/s1/history")

    assert response.status_code == 200
    assert response.json() == [
        {"role": "human", "content": "hola"},
        {"role": "ai", "content": "eco: hola"},
    ]


def test_delete_session(client: TestClient, fake_service: FakeChatService) -> None:
    response = client.delete("/chat/sessions/s1")

    assert response.status_code == 204
    assert fake_service.deleted == ["s1"]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/chat", {"question": "hola", "session_id": "ajena"}),
        ("get", "/chat/sessions/ajena/history", None),
        ("delete", "/chat/sessions/ajena", None),
    ],
)
def test_session_of_another_user_returns_403(
    client: TestClient, fake_service: FakeChatService, method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, path, json=body)

    assert response.status_code == 403
    assert response.json() == {"error": "Acceso denegado", "detail": "La sesión pertenece a otro usuario"}
    assert fake_service.deleted == []


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/chat", {"question": "hola", "session_id": "nope"}),
        ("get", "/chat/sessions/nope/history", None),
        ("delete", "/chat/sessions/nope", None),
    ],
)
def test_unknown_session_returns_404(
    client: TestClient, fake_service: FakeChatService, method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, path, json=body)

    assert response.status_code == 404
    assert response.json() == {"error": "Recurso no encontrado", "detail": "La sesión no existe"}
