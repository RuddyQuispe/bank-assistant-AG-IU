from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.graphs.state.bank_state import BankState
from digital_wallet_rqm.memory.checkpointer import (
    delete_session,
    get_checkpointer,
    get_session_messages,
    list_sessions,
)


def _echo_node(state: BankState) -> dict:
    # Responde con eco del último mensaje para simular el LLM
    return {"messages": [AIMessage(content=f"eco: {state['messages'][-1].text}")]}


def _build_graph(checkpointer):
    builder = StateGraph(BankState)
    builder.add_node("echo", _echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    return builder.compile(checkpointer=checkpointer)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def test_sqlite_checkpointer_persists_messages_per_session(tmp_path):
    db_path = tmp_path / "memory.db"
    with get_checkpointer(backend="sqlite", sqlite_path=db_path) as checkpointer:
        graph = _build_graph(checkpointer)
        graph.invoke({"messages": [HumanMessage(content="hola")]}, _config("s1"))
        graph.invoke({"messages": [HumanMessage(content="saldo")]}, _config("s1"))
        graph.invoke({"messages": [HumanMessage(content="otra")]}, _config("s2"))

    # Reabre la conexión para comprobar que los datos quedaron en disco
    with get_checkpointer(backend="sqlite", sqlite_path=db_path) as checkpointer:
        graph = _build_graph(checkpointer)
        messages = get_session_messages(graph, "s1")
        assert [m.text for m in messages] == ["hola", "eco: hola", "saldo", "eco: saldo"]
        assert sorted(list_sessions(checkpointer)) == ["s1", "s2"]


def test_delete_session_removes_only_that_session(tmp_path):
    with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        graph = _build_graph(checkpointer)
        graph.invoke({"messages": [HumanMessage(content="hola")]}, _config("s1"))
        graph.invoke({"messages": [HumanMessage(content="hola")]}, _config("s2"))

        delete_session(checkpointer, "s1")

        assert list_sessions(checkpointer) == ["s2"]
        assert get_session_messages(graph, "s1") == []


def test_unknown_backend_raises_error():
    import pytest

    with pytest.raises(ValueError, match="mongo"):
        with get_checkpointer(backend="mongo"):
            pass
