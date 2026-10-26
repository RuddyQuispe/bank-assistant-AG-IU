from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from digital_wallet_rqm.infrastructure.agent.state.bank_state import BankState
from digital_wallet_rqm.infrastructure.persistence.checkpointer import get_checkpointer, get_session_messages

pytestmark = pytest.mark.anyio


def _echo_node(state: BankState) -> dict[str, Any]:
    # Responde con eco del último mensaje para simular el LLM
    return {"messages": [AIMessage(content=f"eco: {state['messages'][-1].text}")]}


def _build_graph(checkpointer: BaseCheckpointSaver[str]) -> CompiledStateGraph[Any, Any, Any, Any]:
    builder = StateGraph(BankState)
    builder.add_node("echo", _echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    return builder.compile(checkpointer=checkpointer)


def _config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id}}


async def test_sqlite_checkpointer_persists_messages_per_session(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    async with get_checkpointer(backend="sqlite", sqlite_path=db_path) as checkpointer:
        graph = _build_graph(checkpointer)
        await graph.ainvoke({"messages": [HumanMessage(content="hola")]}, _config("s1"))
        await graph.ainvoke({"messages": [HumanMessage(content="saldo")]}, _config("s1"))
        await graph.ainvoke({"messages": [HumanMessage(content="otra")]}, _config("s2"))

    # Reabre la conexión para comprobar que los datos quedaron en disco
    async with get_checkpointer(backend="sqlite", sqlite_path=db_path) as checkpointer:
        graph = _build_graph(checkpointer)
        messages = await get_session_messages(graph, "s1")
        assert [m.text for m in messages] == ["hola", "eco: hola", "saldo", "eco: saldo"]
        assert [m.text for m in await get_session_messages(graph, "s2")] == ["otra", "eco: otra"]


async def test_unknown_backend_raises_error() -> None:
    with pytest.raises(ValueError, match="mongo"):
        async with get_checkpointer(backend="mongo"):
            pass
