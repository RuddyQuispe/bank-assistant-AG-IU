import pytest
from fastapi.testclient import TestClient

from digital_wallet_rqm.api.dependencies import get_auth_service, get_chat_service, get_document_indexer
from digital_wallet_rqm.api.main import app
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.auth_service import AuthService
from digital_wallet_rqm.services.chat_service import ChatAnswer

SECRET = "test-secret-with-at-least-32-bytes!!"


class FakeChatService:
    """Registra el usuario que llega al servicio"""

    def __init__(self) -> None:
        self.users: list[CurrentUser] = []

    def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        self.users.append(user)
        return ChatAnswer(session_id="s1", response="ok")


class FakeIndexer:
    def sync(self) -> int:
        return 0


@pytest.fixture
def auth_service():
    return AuthService(SECRET)


@pytest.fixture
def chat_service():
    return FakeChatService()


@pytest.fixture
def client(auth_service, chat_service):
    # El filtro de auth es real; solo se reemplazan los servicios que llaman al LLM o a Chroma
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_document_indexer] = lambda: FakeIndexer()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_token_for_demo_user(client, auth_service):
    response = client.post("/auth/token", json={"nickname": "ruddy"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert auth_service.read_user(body["access_token"]) == CurrentUser(user_id="1", nickname="ruddy")


def test_token_for_unknown_user_is_rejected(client):
    response = client.post("/auth/token", json={"nickname": "juan"})

    assert response.status_code == 401


def test_chat_without_token_is_rejected(client, chat_service):
    response = client.post("/chat", json={"question": "hola"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert chat_service.users == []


def test_chat_with_invalid_token_is_rejected(client, chat_service):
    response = client.post("/chat", json={"question": "hola"}, headers={"Authorization": "Bearer no-es-un-jwt"})

    assert response.status_code == 401
    assert chat_service.users == []


def test_chat_receives_the_user_from_the_token(client, chat_service, auth_service):
    token = auth_service.create_token(CurrentUser(user_id="1", nickname="ruddy"))

    response = client.post("/chat", json={"question": "hola"}, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert chat_service.users == [CurrentUser(user_id="1", nickname="ruddy")]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/chat/sessions"),
        ("get", "/chat/sessions/s1/history"),
        ("delete", "/chat/sessions/s1"),
        ("post", "/admin/index"),
    ],
)
def test_other_endpoints_require_token(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401
