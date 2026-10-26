"""Reglas del chat probadas con dobles en memoria: sin LangGraph, sin base de datos, sin FastAPI"""

import uuid
from datetime import UTC, datetime

import pytest

from digital_wallet_rqm.application.chat_use_cases import ChatUseCases
from digital_wallet_rqm.application.ports.outbound.chat_agent import ChatAgent
from digital_wallet_rqm.application.ports.outbound.session_repository import SessionRepository
from digital_wallet_rqm.domain.errors import SessionForbiddenError, SessionNotFoundError
from digital_wallet_rqm.domain.models import ChatMessage, ChatSession, CurrentUser, build_title

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
OTHER = CurrentUser(user_id="2", nickname="otro")


class FakeAgent(ChatAgent):
    """Agente de eco: guarda el historial en un dict"""

    def __init__(self, fail: bool = False) -> None:
        self.histories: dict[str, list[ChatMessage]] = {}
        self.calls: list[str] = []
        self.fail = fail

    async def answer(self, question: str, session_id: str, user: CurrentUser) -> str:
        if self.fail:
            raise RuntimeError("el LLM no responde")
        response = f"eco: {question}"
        history = self.histories.setdefault(session_id, [])
        history += [ChatMessage("human", question), ChatMessage("ai", response)]
        return response

    async def history(self, session_id: str) -> list[ChatMessage]:
        return list(self.histories.get(session_id, []))

    async def forget(self, session_id: str) -> None:
        self.calls.append(f"forget {session_id}")
        self.histories.pop(session_id, None)


class FakeSessions(SessionRepository):
    """Repositorio en memoria con el mismo contrato que la tabla "sessions" """

    def __init__(self, calls: list[str]) -> None:
        self.rows: dict[str, ChatSession] = {}
        self.calls = calls
        self.clock = 0

    def _tick(self) -> datetime:
        # Reloj determinista: cada operación avanza un segundo
        self.clock += 1
        return datetime.fromtimestamp(self.clock, UTC)

    async def create(self, user_id: str) -> ChatSession:
        now = self._tick()
        session = ChatSession(str(uuid.uuid4()), user_id, None, now, now)
        self.rows[session.session_id] = session
        return session

    async def find(self, session_id: str) -> ChatSession | None:
        return self.rows.get(session_id)

    async def list_for_user(self, user_id: str) -> list[ChatSession]:
        own = [row for row in self.rows.values() if row.user_id == user_id]
        return sorted(own, key=lambda row: row.updated_at, reverse=True)

    async def record_question(self, session_id: str, question: str) -> None:
        row = self.rows[session_id]
        title = row.title or build_title(question)
        self.rows[session_id] = ChatSession(row.session_id, row.user_id, title, row.created_at, self._tick())

    async def delete(self, session_id: str) -> None:
        self.calls.append(f"delete {session_id}")
        self.rows.pop(session_id, None)


@pytest.fixture
def agent() -> FakeAgent:
    return FakeAgent()


@pytest.fixture
def chat(agent: FakeAgent) -> ChatUseCases:
    return ChatUseCases(agent=agent, sessions=FakeSessions(agent.calls))


async def test_ask_without_session_creates_one_with_a_server_uuid(chat: ChatUseCases) -> None:
    answer = await chat.ask("hola", RUDDY)

    assert uuid.UUID(answer.session_id).version == 4
    assert answer.response == "eco: hola"
    assert [session.session_id for session in await chat.list_sessions(RUDDY)] == [answer.session_id]


async def test_ask_keeps_using_an_existing_session(chat: ChatUseCases) -> None:
    session = await chat.create_session(RUDDY)

    answer = await chat.ask("hola", RUDDY, session_id=session.session_id)

    assert answer.session_id == session.session_id


async def test_ask_with_unknown_session_id_is_not_found(chat: ChatUseCases) -> None:
    # El cliente no puede inventar ids: las sesiones nuevas se piden sin session_id
    with pytest.raises(SessionNotFoundError):
        await chat.ask("hola", RUDDY, session_id="inventada")


async def test_first_question_becomes_the_session_title(chat: ChatUseCases) -> None:
    answer = await chat.ask("¿Cuánto cuesta un SPEI?", RUDDY)
    await chat.ask("gracias", RUDDY, session_id=answer.session_id)

    [session] = await chat.list_sessions(RUDDY)
    assert session.title == "¿Cuánto cuesta un SPEI?"


async def test_created_session_has_no_title_until_the_first_question(chat: ChatUseCases) -> None:
    session = await chat.create_session(RUDDY)

    assert session.title is None


async def test_failed_answer_records_no_activity(agent: FakeAgent) -> None:
    agent.fail = True
    sessions = FakeSessions(agent.calls)
    chat = ChatUseCases(agent=agent, sessions=sessions)
    session = await chat.create_session(RUDDY)

    with pytest.raises(RuntimeError):
        await chat.ask("hola", RUDDY, session_id=session.session_id)

    assert sessions.rows[session.session_id] == session


async def test_history_comes_from_the_agent(chat: ChatUseCases) -> None:
    answer = await chat.ask("hola", RUDDY)
    await chat.ask("saldo", RUDDY, session_id=answer.session_id)

    history = await chat.get_history(RUDDY, answer.session_id)

    assert history == [
        ChatMessage(role="human", content="hola"),
        ChatMessage(role="ai", content="eco: hola"),
        ChatMessage(role="human", content="saldo"),
        ChatMessage(role="ai", content="eco: saldo"),
    ]


async def test_delete_forgets_the_history_before_deleting_the_session(chat: ChatUseCases, agent: FakeAgent) -> None:
    first = await chat.ask("hola", RUDDY)
    second = await chat.ask("hola", RUDDY)

    await chat.delete_session(RUDDY, first.session_id)

    # Si falla entre los dos pasos, la sesión sigue listada y se puede volver a borrar
    assert agent.calls == [f"forget {first.session_id}", f"delete {first.session_id}"]
    assert [session.session_id for session in await chat.list_sessions(RUDDY)] == [second.session_id]
    with pytest.raises(SessionNotFoundError):
        await chat.get_history(RUDDY, first.session_id)


async def test_list_sessions_returns_only_own_sessions(chat: ChatUseCases) -> None:
    mine = await chat.ask("hola", RUDDY)
    theirs = await chat.ask("hola", OTHER)

    assert [session.session_id for session in await chat.list_sessions(RUDDY)] == [mine.session_id]
    assert [session.session_id for session in await chat.list_sessions(OTHER)] == [theirs.session_id]


async def test_session_of_another_user_is_forbidden(chat: ChatUseCases, agent: FakeAgent) -> None:
    theirs = await chat.ask("secreto", OTHER)

    with pytest.raises(SessionForbiddenError):
        await chat.ask("hola", RUDDY, session_id=theirs.session_id)
    with pytest.raises(SessionForbiddenError):
        await chat.get_history(RUDDY, theirs.session_id)
    with pytest.raises(SessionForbiddenError):
        await chat.delete_session(RUDDY, theirs.session_id)

    # La sesión ajena queda intacta
    assert agent.calls == []
    assert [m.content for m in await chat.get_history(OTHER, theirs.session_id)] == ["secreto", "eco: secreto"]
