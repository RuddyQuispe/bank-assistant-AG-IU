from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.exceptions import SessionForbiddenError
from digital_wallet_rqm.graphs.state.bank_state import BankState
from digital_wallet_rqm.memory.checkpoint_session_repository import CheckpointSessionRepository
from digital_wallet_rqm.memory.checkpointer import get_checkpointer
from digital_wallet_rqm.models.current_user import CurrentUser
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
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        builder = StateGraph(BankState)
        builder.add_node("echo", _echo_node)
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)
        agent: Any = builder.compile(checkpointer=checkpointer)
        # El grafo de prueba no usa el vector store
        yield LangGraphChatService(agent, CheckpointSessionRepository(checkpointer), vector_store=None)  # type: ignore[arg-type]


async def test_ask_returns_response_and_keeps_session(service: LangGraphChatService) -> None:
    answer = await service.ask("hola", RUDDY, session_id="s1")

    assert answer.session_id == "s1"
    assert answer.response == "eco: hola"


async def test_ask_without_session_creates_a_new_one(service: LangGraphChatService) -> None:
    answer = await service.ask("hola", RUDDY)

    assert answer.session_id != ""
    assert await service.list_sessions(RUDDY) == [answer.session_id]


async def test_history_has_user_and_ai_messages_in_order(service: LangGraphChatService) -> None:
    await service.ask("hola", RUDDY, session_id="s1")
    await service.ask("saldo", RUDDY, session_id="s1")

    history = await service.get_history(RUDDY, "s1")

    assert history == [
        ChatMessage(role="human", content="hola"),
        ChatMessage(role="ai", content="eco: hola"),
        ChatMessage(role="human", content="saldo"),
        ChatMessage(role="ai", content="eco: saldo"),
    ]


async def test_delete_session_removes_it(service: LangGraphChatService) -> None:
    await service.ask("hola", RUDDY, session_id="s1")
    await service.ask("hola", RUDDY, session_id="s2")

    await service.delete_session(RUDDY, "s1")

    assert await service.list_sessions(RUDDY) == ["s2"]
    assert await service.get_history(RUDDY, "s1") == []


async def test_list_sessions_returns_only_own_sessions(service: LangGraphChatService) -> None:
    await service.ask("hola", RUDDY, session_id="mia")
    await service.ask("hola", OTHER, session_id="ajena")

    assert await service.list_sessions(RUDDY) == ["mia"]
    assert await service.list_sessions(OTHER) == ["ajena"]


async def test_session_of_another_user_is_forbidden(service: LangGraphChatService) -> None:
    await service.ask("secreto", OTHER, session_id="ajena")

    with pytest.raises(SessionForbiddenError):
        await service.ask("hola", RUDDY, session_id="ajena")
    with pytest.raises(SessionForbiddenError):
        await service.get_history(RUDDY, "ajena")
    with pytest.raises(SessionForbiddenError):
        await service.delete_session(RUDDY, "ajena")

    # La sesión ajena queda intacta
    assert [m.content for m in await service.get_history(OTHER, "ajena")] == ["secreto", "eco: secreto"]
