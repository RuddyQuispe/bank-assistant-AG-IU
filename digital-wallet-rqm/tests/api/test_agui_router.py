import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime

from digital_wallet_rqm.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_rag_agent,
    get_session_repository,
    get_vector_store,
)
from digital_wallet_rqm.api.main import app
from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.rag_agent import HIDDEN_FROM_CHAT
from digital_wallet_rqm.graphs.state.bank_state import BankState
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.models.session import ChatSession, build_title
from digital_wallet_rqm.services.auth_service import AuthService
from digital_wallet_rqm.services.session_repository import SessionRepository

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
NOW = datetime(2026, 10, 26, tzinfo=UTC)


class InMemorySessionRepository(SessionRepository):
    """Repositorio en memoria: los tests del adaptador no necesitan base de datos"""

    def __init__(self) -> None:
        self.sessions: dict[str, ChatSession] = {}
        self.questions: list[tuple[str, str]] = []

    def add(self, session_id: str, user_id: str) -> None:
        self.sessions[session_id] = ChatSession(session_id, user_id, None, NOW, NOW)

    async def create(self, user_id: str) -> ChatSession:
        raise NotImplementedError

    async def find(self, session_id: str) -> ChatSession | None:
        return self.sessions.get(session_id)

    async def list_for_user(self, user_id: str) -> list[ChatSession]:
        return [session for session in self.sessions.values() if session.user_id == user_id]

    async def record_question(self, session_id: str, question: str) -> None:
        self.questions.append((session_id, build_title(question)))

    async def delete(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)


def _hidden_node(state: BankState) -> dict[str, Any]:
    # Simula el analyzer: su LLM no debe llegar al chat
    GenericFakeChatModel(messages=iter([AIMessage(content="ruta interna")])).invoke("x")
    return {}


def _answer_node(state: BankState, runtime: Runtime[GraphContext]) -> dict[str, Any]:
    # Simula el interpreter: responde con el usuario del contexto tipado
    user = runtime.context.user
    llm = GenericFakeChatModel(messages=iter([AIMessage(content=f"hola {user.nickname if user else '?'}")]))
    return {"messages": [llm.invoke("x")]}


def _failing_node(state: BankState) -> dict[str, Any]:
    raise RuntimeError("Gemini no responde")


def _build_graph(*nodes: tuple[object, dict[str, bool] | None]) -> object:
    builder = StateGraph(BankState, context_schema=GraphContext, input_schema=MessagesState)
    names = []
    for index, (node, metadata) in enumerate(nodes):
        name = f"node_{index}"
        builder.add_node(name, node, metadata=metadata)  # type: ignore[call-overload]
        names.append(name)
    builder.add_edge(START, names[0])
    for current, following in zip(names, names[1:], strict=False):
        builder.add_edge(current, following)
    builder.add_edge(names[-1], END)
    return builder.compile(checkpointer=InMemorySaver())


class Env:
    def __init__(self) -> None:
        self.graph = _build_graph((_hidden_node, HIDDEN_FROM_CHAT), (_answer_node, None))
        self.sessions = InMemorySessionRepository()
        self.sessions.add("s1", RUDDY.user_id)


@pytest.fixture
def env() -> Iterator[Env]:
    environment = Env()
    app.dependency_overrides[get_rag_agent] = lambda: environment.graph
    app.dependency_overrides[get_session_repository] = lambda: environment.sessions
    app.dependency_overrides[get_vector_store] = lambda: InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    yield environment
    app.dependency_overrides.clear()


@pytest.fixture
def client(env: Env) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: RUDDY
    # Sin "with": no se ejecuta el lifespan, así no se abre la base ni Chroma
    return TestClient(app)


def _run_input(thread_id: str, text: str = "hola") -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "runId": "run-1",
        "state": {},
        "messages": [{"id": "m-1", "role": "user", "content": text}],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


def _events(body: str) -> list[dict[str, Any]]:
    return [json.loads(line.removeprefix("data: ")) for line in body.splitlines() if line.startswith("data: ")]


def test_run_streams_ag_ui_events_with_the_answer(client: TestClient) -> None:
    response = client.post("/agents/wallet", json=_run_input("s1"), headers={"Accept": "text/event-stream"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    types = [event["type"] for event in events]
    assert types[0] == "RUN_STARTED"
    assert types[-1] == "RUN_FINISHED"
    streamed = "".join(event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CONTENT")
    # La respuesta lleva al usuario del token (contexto tipado) y el LLM oculto no aparece
    assert streamed == "hola ruddy"


def test_streamed_message_id_matches_the_saved_message(client: TestClient) -> None:
    events = _events(client.post("/agents/wallet", json=_run_input("s1")).text)

    started = [event["messageId"] for event in events if event["type"] == "TEXT_MESSAGE_START"]
    snapshot = next(event for event in events if event["type"] == "MESSAGES_SNAPSHOT")
    assistant_ids = [message["id"] for message in snapshot["messages"] if message["role"] == "assistant"]
    # Mismo id: el frontend no muestra la respuesta dos veces
    assert started == assistant_ids


def test_finished_run_records_the_question_for_the_title(client: TestClient, env: Env) -> None:
    client.post("/agents/wallet", json=_run_input("s1", "¿Cuánto cuesta\nun SPEI?"))

    assert env.sessions.questions == [("s1", "¿Cuánto cuesta un SPEI?")]


def test_failed_run_ends_with_run_error_and_records_nothing(client: TestClient, env: Env) -> None:
    env.graph = _build_graph((_failing_node, None))

    response = client.post("/agents/wallet", json=_run_input("s1"))

    # El 200 ya se envió al abrir el stream: el error llega como evento, no como status
    assert response.status_code == 200
    assert _events(response.text)[-1]["type"] == "RUN_ERROR"
    assert env.sessions.questions == []


def test_unknown_thread_returns_404(client: TestClient) -> None:
    response = client.post("/agents/wallet", json=_run_input("inventado"))

    assert response.status_code == 404
    assert response.json() == {"error": "Recurso no encontrado", "detail": "La sesión no existe"}


def test_session_of_another_user_returns_403(client: TestClient, env: Env) -> None:
    env.sessions.add("ajena", "2")

    response = client.post("/agents/wallet", json=_run_input("ajena"))

    assert response.status_code == 403
    assert response.json() == {"error": "Acceso denegado", "detail": "La sesión pertenece a otro usuario"}


def test_run_without_token_returns_401(env: Env) -> None:
    app.dependency_overrides[get_auth_service] = lambda: AuthService("test-secret")

    response = TestClient(app).post("/agents/wallet", json=_run_input("s1"))

    assert response.status_code == 401
    assert response.json() == {"error": "No autenticado", "detail": "Falta el token"}


def test_cors_allows_the_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/agents/wallet",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
