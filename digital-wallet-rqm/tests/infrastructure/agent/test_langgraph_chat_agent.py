"""Adaptador ChatAgent sobre un grafo de prueba y el checkpointer SQLite real"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.domain.models import ChatMessage, CurrentUser
from digital_wallet_rqm.infrastructure.agent.langgraph_chat_agent import LangGraphChatAgent
from digital_wallet_rqm.infrastructure.agent.state.bank_state import BankState
from digital_wallet_rqm.infrastructure.persistence.checkpointer import get_checkpointer

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")


def _echo_node(state: BankState) -> dict[str, Any]:
    # Simula el grafo RAG: responde con eco del último mensaje
    response = f"eco: {state['messages'][-1].text}"
    return {"response": response, "messages": [AIMessage(content=response)]}


@pytest.fixture
async def agent(tmp_path: Path) -> AsyncIterator[LangGraphChatAgent]:
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        builder = StateGraph(BankState)
        builder.add_node("echo", _echo_node)
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)
        graph: Any = builder.compile(checkpointer=checkpointer)
        # El grafo de prueba no usa el vector store
        yield LangGraphChatAgent(graph, checkpointer, vector_store=None)  # type: ignore[arg-type]


async def test_answer_returns_the_graph_response(agent: LangGraphChatAgent) -> None:
    assert await agent.answer("hola", "s1", RUDDY) == "eco: hola"


async def test_history_keeps_both_turns_per_session(agent: LangGraphChatAgent) -> None:
    await agent.answer("hola", "s1", RUDDY)
    await agent.answer("saldo", "s1", RUDDY)
    await agent.answer("otra", "s2", RUDDY)

    assert await agent.history("s1") == [
        ChatMessage(role="human", content="hola"),
        ChatMessage(role="ai", content="eco: hola"),
        ChatMessage(role="human", content="saldo"),
        ChatMessage(role="ai", content="eco: saldo"),
    ]


async def test_forget_removes_only_that_session_history(agent: LangGraphChatAgent) -> None:
    await agent.answer("hola", "s1", RUDDY)
    await agent.answer("hola", "s2", RUDDY)

    await agent.forget("s1")

    assert await agent.history("s1") == []
    assert len(await agent.history("s2")) == 2
