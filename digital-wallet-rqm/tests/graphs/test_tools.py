from collections.abc import Sequence
from types import SimpleNamespace

import pytest
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.nodes import tools
from digital_wallet_rqm.graphs.nodes.tools import node_tools
from digital_wallet_rqm.graphs.tools import TOOLS
from digital_wallet_rqm.models.current_user import CurrentUser

RUDDY = CurrentUser(user_id="1", nickname="ruddy")


class _FakeLLM:
    def __init__(self, reply: AIMessage) -> None:
        self.reply = reply
        self.bound_tools: Sequence[BaseTool] = []
        self.received: list[BaseMessage] = []

    def bind_tools(self, bound: Sequence[BaseTool]) -> Runnable[LanguageModelInput, AIMessage]:
        self.bound_tools = bound

        def _invoke(messages: list[BaseMessage]) -> AIMessage:
            self.received = messages
            return self.reply

        return RunnableLambda(_invoke)


def _patch_llm(monkeypatch: pytest.MonkeyPatch, reply: AIMessage) -> _FakeLLM:
    fake = _FakeLLM(reply)
    monkeypatch.setattr(tools, "get_llm", lambda temperature: fake)
    return fake


def _state(question: str) -> dict[str, object]:
    return {"messages": [HumanMessage(content="mensaje previo")], "question": question}


def _runtime(user: CurrentUser | None = RUDDY) -> SimpleNamespace:
    # Simula el Runtime de LangGraph: el nodo solo usa runtime.context
    return SimpleNamespace(context=GraphContext(vector_store=None, user=user))


def test_binds_tools_and_sends_the_question(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_llm(monkeypatch, AIMessage(content=""))

    node_tools(_state("cuánto tengo"), _runtime())

    assert list(fake.bound_tools) == TOOLS
    assert isinstance(fake.received[0], SystemMessage)
    assert fake.received[1:] == [HumanMessage(content="cuánto tengo")]


def test_executes_requested_tool_and_returns_its_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = node_tools(_state("cuánto tengo"), _runtime())

    assert result == {"tool_results": [{"tool": "get_balance", "content": "Saldo disponible de ruddy: 1,500.50 Bs"}]}


def test_unknown_tool_returns_error_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = AIMessage(content="", tool_calls=[{"name": "transfer", "args": {}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = node_tools(_state("transfiere 100"), _runtime())

    assert result == {"tool_results": [{"tool": "transfer", "content": "Error: herramienta no disponible."}]}


def test_returns_empty_results_when_no_tool_is_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, AIMessage(content="no necesito herramientas"))

    result = node_tools(_state("hola"), _runtime())

    assert result == {"tool_results": []}
    assert "messages" not in result


def test_llm_cannot_choose_the_user(monkeypatch: pytest.MonkeyPatch) -> None:
    # Aunque el LLM intente pasar otro usuario, se usa siempre el del token
    other = {"user_id": "2", "nickname": "juan"}
    reply = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {"user": other}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = node_tools(_state("saldo de juan"), _runtime())

    assert result == {"tool_results": [{"tool": "get_balance", "content": "Saldo disponible de ruddy: 1,500.50 Bs"}]}


def test_user_is_hidden_from_the_llm() -> None:
    get_balance = next(tool for tool in TOOLS if tool.name == "get_balance")

    assert "user" not in get_balance.tool_call_schema.model_json_schema().get("properties", {})


def test_tool_without_user_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = node_tools(_state("cuánto tengo"), _runtime(user=None))

    assert result == {"tool_results": [{"tool": "get_balance", "content": "Error: usuario no autenticado."}]}


def test_unknown_user_has_no_account(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = node_tools(_state("cuánto tengo"), _runtime(user=CurrentUser(user_id="99", nickname="nadie")))

    assert result == {"tool_results": [{"tool": "get_balance", "content": "No se encontró una cuenta para nadie."}]}
