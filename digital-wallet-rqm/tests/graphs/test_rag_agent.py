from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool
from langchain_core.vectorstores import InMemoryVectorStore
from langgraph.checkpoint.memory import InMemorySaver

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.nodes import analyzer, interpreter, tools
from digital_wallet_rqm.graphs.rag_agent import RagAgent, build_rag_agent
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.models.route_decision_node import RouteDecision
from digital_wallet_rqm.models.types import Route


class _FakeToolsLLM:
    def bind_tools(self, bound: Sequence[BaseTool]) -> Runnable[LanguageModelInput, AIMessage]:
        call = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {}, "id": "call-1"}])
        return RunnableLambda(lambda _: call)


@pytest.fixture
def interpreter_input(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Fakes every LLM; returns the human prompts the interpreter received"""
    received: list[str] = []

    def _answer(prompt: PromptValue) -> str:
        received.append(prompt.to_messages()[-1].text)
        return f"respuesta {len(received)}"

    monkeypatch.setattr(interpreter, "get_llm", lambda temperature, response_format: RunnableLambda(_answer))
    monkeypatch.setattr(tools, "get_llm", lambda temperature: _FakeToolsLLM())
    return received


def _route_to(monkeypatch: pytest.MonkeyPatch, route: Route) -> None:
    decision = RouteDecision(route=route, reason="test")
    monkeypatch.setattr(analyzer, "get_llm", lambda temperature, response_format: RunnableLambda(lambda _: decision))


def _context() -> GraphContext:
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    doc = Document(page_content="El SPEI no tiene costo.", metadata={"file_name": "faq.pdf", "page": 0})
    store.add_documents([doc])
    return GraphContext(vector_store=store, user=CurrentUser(user_id="1", nickname="ruddy"))


def _ask(question: str, graph: RagAgent | None = None, config: RunnableConfig | None = None) -> dict[str, Any]:
    result: dict[str, Any] = (graph or build_rag_agent()).invoke(
        {"messages": [HumanMessage(content=question)], "question": question}, config=config, context=_context()
    )
    return result


def test_graph_compiles_with_all_nodes() -> None:
    graph = build_rag_agent()

    assert {"analyzer", "retrieve", "tools", "interpreter"} <= set(graph.get_graph().nodes)


def test_tools_route_runs_tools_node(monkeypatch: pytest.MonkeyPatch, interpreter_input: list[str]) -> None:
    _route_to(monkeypatch, "tools")

    result = _ask("cuánto tengo")

    assert result["tool_results"] == [{"tool": "get_balance", "content": "Saldo disponible de ruddy: 1,500.50 Bs"}]
    assert "get_balance: Saldo disponible de ruddy: 1,500.50 Bs" in interpreter_input[0]
    assert result["response"] == "respuesta 1"


def test_retrieve_route_uses_vector_store_from_context(
    monkeypatch: pytest.MonkeyPatch, interpreter_input: list[str]
) -> None:
    _route_to(monkeypatch, "retrieve")

    result = _ask("cuánto cuesta un SPEI")

    assert result["retrieve_docs"] == ["El SPEI no tiene costo."]
    assert "[faq.pdf, pág. 1] El SPEI no tiene costo." in interpreter_input[0]


def test_analyst_route_goes_straight_to_interpreter(
    monkeypatch: pytest.MonkeyPatch, interpreter_input: list[str]
) -> None:
    _route_to(monkeypatch, "analyst")

    result = _ask("gracias")

    assert "retrieve_docs" not in result
    assert "tool_results" not in result
    assert "Información: Ninguna (saludo o aclaración)" in interpreter_input[0]


def test_checkpointer_keeps_history_per_thread(monkeypatch: pytest.MonkeyPatch, interpreter_input: list[str]) -> None:
    _route_to(monkeypatch, "analyst")
    graph = build_rag_agent(checkpointer=InMemorySaver())
    config: RunnableConfig = {"configurable": {"thread_id": "sesion-1"}}

    _ask("hola", graph=graph, config=config)
    result = _ask("gracias", graph=graph, config=config)

    assert [message.text for message in result["messages"]] == ["hola", "respuesta 1", "gracias", "respuesta 2"]
