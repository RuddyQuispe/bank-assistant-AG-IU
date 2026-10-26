import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.api.dependencies import get_chat_service, get_current_user
from digital_wallet_rqm.api.main import app
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatAnswer, ChatMessage, ChatService


class FakeChatService(ChatService):
    """Servicio falso: evita llamar al LLM y a la base de datos"""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        return ChatAnswer(session_id=session_id or "new-session", response=f"eco: {question}")

    async def list_sessions(self) -> list[str]:
        return ["s1", "s2"]

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        return [ChatMessage(role="human", content="hola"), ChatMessage(role="ai", content="eco: hola")]

    async def delete_session(self, session_id: str) -> None:
        self.deleted.append(session_id)


@pytest.fixture
def fake_service():
    service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id="1", nickname="ruddy")
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client(fake_service):
    # Sin "with": no se ejecuta el lifespan, así no se abre la base ni Chroma
    return TestClient(app)


def test_post_chat_returns_answer(client):
    response = client.post("/chat", json={"question": "hola", "session_id": "s1"})

    assert response.status_code == 200
    assert response.json() == {"session_id": "s1", "response": "eco: hola"}


def test_post_chat_without_session_returns_new_session(client):
    response = client.post("/chat", json={"question": "hola"})

    assert response.status_code == 200
    assert response.json()["session_id"] == "new-session"


def test_post_chat_rejects_empty_question(client):
    response = client.post("/chat", json={"question": ""})

    assert response.status_code == 422


def test_get_sessions(client):
    response = client.get("/chat/sessions")

    assert response.status_code == 200
    assert response.json() == ["s1", "s2"]


def test_get_history(client):
    response = client.get("/chat/sessions/s1/history")

    assert response.status_code == 200
    assert response.json() == [
        {"role": "human", "content": "hola"},
        {"role": "ai", "content": "eco: hola"},
    ]


def test_delete_session(client, fake_service):
    response = client.delete("/chat/sessions/s1")

    assert response.status_code == 204
    assert fake_service.deleted == ["s1"]
