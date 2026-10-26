import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.graphs.state.bank_state import BankState
from digital_wallet_rqm.memory.checkpointer import get_checkpointer
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatMessage
from digital_wallet_rqm.services.langgraph_chat_service import LangGraphChatService

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")


def _echo_node(state: BankState) -> dict:
    # Simula el agente: responde con eco del último mensaje (el servicio ya no envía "question")
    response = f"eco: {state['messages'][-1].text}"
    return {"response": response, "messages": [AIMessage(content=response)]}


def _build_service(checkpointer) -> LangGraphChatService:
    builder = StateGraph(BankState)
    builder.add_node("echo", _echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    agent = builder.compile(checkpointer=checkpointer)
    # El grafo de prueba no usa el vector store
    return LangGraphChatService(agent, checkpointer, vector_store=None)


async def test_ask_returns_response_and_keeps_session(tmp_path):
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)

        answer = await service.ask("hola", RUDDY, session_id="s1")

        assert answer.session_id == "s1"
        assert answer.response == "eco: hola"


async def test_ask_without_session_creates_a_new_one(tmp_path):
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)

        answer = await service.ask("hola", RUDDY)

        assert answer.session_id != ""
        assert await service.list_sessions() == [answer.session_id]


async def test_history_has_user_and_ai_messages_in_order(tmp_path):
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)
        await service.ask("hola", RUDDY, session_id="s1")
        await service.ask("saldo", RUDDY, session_id="s1")

        history = await service.get_history("s1")

        assert history == [
            ChatMessage(role="human", content="hola"),
            ChatMessage(role="ai", content="eco: hola"),
            ChatMessage(role="human", content="saldo"),
            ChatMessage(role="ai", content="eco: saldo"),
        ]


async def test_delete_session_removes_it(tmp_path):
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)
        await service.ask("hola", RUDDY, session_id="s1")
        await service.ask("hola", RUDDY, session_id="s2")

        await service.delete_session("s1")

        assert await service.list_sessions() == ["s2"]
        assert await service.get_history("s1") == []
