import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.exceptions import SessionForbiddenError, SessionNotFoundError
from digital_wallet_rqm.graphs.state.bank_state import BankState
from digital_wallet_rqm.memory.checkpointer import get_checkpointer
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.persistence.database import database_url, get_engine
from digital_wallet_rqm.persistence.repositories import SqlSessionRepository
from digital_wallet_rqm.services.chat_service import ChatMessage
from digital_wallet_rqm.services.langgraph_chat_service import LangGraphChatService

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
OTHER = CurrentUser(user_id="2", nickname="otro")


def _echo_node(state: BankState) -> dict[str, Any]:
    # Simula el agente: responde con eco del último mensaje (el servicio ya no envía "question")
    response = f"eco: {state['messages'][-1].text}"
    return {"response": response, "messages": [AIMessage(content=response)]}


@pytest.fixture
async def service(tmp_path: Path) -> AsyncIterator[LangGraphChatService]:
    db_path = tmp_path / "memory.db"
    async with (
        get_checkpointer(backend="sqlite", sqlite_path=db_path) as checkpointer,
        get_engine(database_url(backend="sqlite", sqlite_path=db_path)) as engine,
    ):
        builder = StateGraph(BankState)
        builder.add_node("echo", _echo_node)
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)
        agent: Any = builder.compile(checkpointer=checkpointer)
        # El grafo de prueba no usa el vector store
        yield LangGraphChatService(agent, SqlSessionRepository(engine, checkpointer), vector_store=None)  # type: ignore[arg-type]


async def test_ask_without_session_creates_one_with_a_server_uuid(service: LangGraphChatService) -> None:
    answer = await service.ask("hola", RUDDY)

    assert uuid.UUID(answer.session_id).version == 4
    assert answer.response == "eco: hola"
    assert [session.session_id for session in await service.list_sessions(RUDDY)] == [answer.session_id]


async def test_ask_keeps_using_an_existing_session(service: LangGraphChatService) -> None:
    session = await service.create_session(RUDDY)

    answer = await service.ask("hola", RUDDY, session_id=session.session_id)

    assert answer.session_id == session.session_id


async def test_ask_with_unknown_session_id_is_not_found(service: LangGraphChatService) -> None:
    # El cliente no puede inventar ids: las sesiones nuevas se piden sin session_id
    with pytest.raises(SessionNotFoundError):
        await service.ask("hola", RUDDY, session_id="inventada")


async def test_first_question_becomes_the_session_title(service: LangGraphChatService) -> None:
    answer = await service.ask("¿Cuánto cuesta un SPEI?", RUDDY)
    await service.ask("gracias", RUDDY, session_id=answer.session_id)

    [session] = await service.list_sessions(RUDDY)
    assert session.title == "¿Cuánto cuesta un SPEI?"


async def test_created_session_has_no_title_until_the_first_question(service: LangGraphChatService) -> None:
    session = await service.create_session(RUDDY)

    assert session.title is None


async def test_history_has_user_and_ai_messages_in_order(service: LangGraphChatService) -> None:
    answer = await service.ask("hola", RUDDY)
    await service.ask("saldo", RUDDY, session_id=answer.session_id)

    history = await service.get_history(RUDDY, answer.session_id)

    assert history == [
        ChatMessage(role="human", content="hola"),
        ChatMessage(role="ai", content="eco: hola"),
        ChatMessage(role="human", content="saldo"),
        ChatMessage(role="ai", content="eco: saldo"),
    ]


async def test_delete_session_removes_it(service: LangGraphChatService) -> None:
    first = await service.ask("hola", RUDDY)
    second = await service.ask("hola", RUDDY)

    await service.delete_session(RUDDY, first.session_id)

    assert [session.session_id for session in await service.list_sessions(RUDDY)] == [second.session_id]
    with pytest.raises(SessionNotFoundError):
        await service.get_history(RUDDY, first.session_id)


async def test_list_sessions_returns_only_own_sessions(service: LangGraphChatService) -> None:
    mine = await service.ask("hola", RUDDY)
    theirs = await service.ask("hola", OTHER)

    assert [session.session_id for session in await service.list_sessions(RUDDY)] == [mine.session_id]
    assert [session.session_id for session in await service.list_sessions(OTHER)] == [theirs.session_id]


async def test_session_of_another_user_is_forbidden(service: LangGraphChatService) -> None:
    theirs = await service.ask("secreto", OTHER)

    with pytest.raises(SessionForbiddenError):
        await service.ask("hola", RUDDY, session_id=theirs.session_id)
    with pytest.raises(SessionForbiddenError):
        await service.get_history(RUDDY, theirs.session_id)
    with pytest.raises(SessionForbiddenError):
        await service.delete_session(RUDDY, theirs.session_id)

    # La sesión ajena queda intacta
    assert [m.content for m in await service.get_history(OTHER, theirs.session_id)] == ["secreto", "eco: secreto"]
