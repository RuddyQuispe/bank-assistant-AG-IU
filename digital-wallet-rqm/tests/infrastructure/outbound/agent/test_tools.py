from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool

from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import SHOW_ACCOUNT_BALANCE
from digital_wallet_rqm.infrastructure.outbound.agent.nodes import tools
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import MANUALLY_EMIT_TOOL_CALL
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.tools import node_tools
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import ToolsUpdate
from digital_wallet_rqm.infrastructure.outbound.agent.tools import TOOLS

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
BALANCE_TEXT = "Saldo disponible de ruddy en Caja de ahorro ****4567: 1,500.50 Bs"
GET_BALANCE = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {}, "id": "call-1"}])
# Lo que declara el navegador para decir que sabe dibujar la tarjeta del saldo
BALANCE_CARD_TOOL = {"name": SHOW_ACCOUNT_BALANCE, "description": "Muestra el saldo", "parameters": {}}


class _FakeLLM:
    def __init__(self, reply: AIMessage) -> None:
        self.reply = reply
        self.bound_tools: Sequence[BaseTool] = []
        self.received: list[BaseMessage] = []

    def bind_tools(self, bound: Sequence[BaseTool]) -> Runnable[LanguageModelInput, AIMessage]:
        self.bound_tools = bound
        return RunnableLambda(self._invoke)

    def _invoke(self, messages: list[BaseMessage]) -> AIMessage:
        self.received = messages
        return self.reply


def _patch_llm(monkeypatch: pytest.MonkeyPatch, reply: AIMessage) -> _FakeLLM:
    fake = _FakeLLM(reply)
    monkeypatch.setattr(tools, "get_llm", lambda temperature: fake)
    return fake


def _state(question: str, client_tools: list[dict[str, Any]] | None = None) -> dict[str, object]:
    state: dict[str, object] = {"messages": [HumanMessage(content="mensaje previo")], "question": question}
    if client_tools is not None:
        state["tools"] = client_tools
    return state


def _runtime(user: CurrentUser | None = RUDDY) -> SimpleNamespace:
    # Simula el Runtime de LangGraph: el nodo solo usa runtime.context
    return SimpleNamespace(context=GraphContext(vector_store=None, user=user))


class _EmittedEvents(BaseCallbackHandler):
    """Guarda los eventos custom que emite el nodo (lo que AG-UI convierte en TOOL_CALL_*)"""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def on_custom_event(self, name: str, data: object, **kwargs: object) -> None:
        self.events.append((name, data))


def _run_node(
    state: dict[str, object], runtime: SimpleNamespace | None = None, emitted: _EmittedEvents | None = None
) -> ToolsUpdate:
    # Como en el grafo: el nodo corre dentro de un Runnable (necesita config para emitir eventos)
    graph_runtime = runtime or _runtime()
    node = RunnableLambda(lambda node_state: node_tools(node_state, graph_runtime))
    result: ToolsUpdate = node.invoke(state, config={"callbacks": [emitted] if emitted else []})
    return result


def test_binds_tools_and_sends_the_question(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_llm(monkeypatch, AIMessage(content=""))

    _run_node(_state("cuánto tengo"))

    assert list(fake.bound_tools) == TOOLS
    assert isinstance(fake.received[0], SystemMessage)
    assert fake.received[1:] == [HumanMessage(content="cuánto tengo")]


def test_executes_requested_tool_and_returns_its_result(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)

    result = _run_node(_state("cuánto tengo"))

    assert result == {"tool_results": [{"tool": "get_balance", "content": BALANCE_TEXT}]}


def test_unknown_tool_returns_error_result(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = AIMessage(content="", tool_calls=[{"name": "transfer", "args": {}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = _run_node(_state("transfiere 100"))

    assert result == {"tool_results": [{"tool": "transfer", "content": "Error: herramienta no disponible."}]}


def test_returns_empty_results_when_no_tool_is_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, AIMessage(content="no necesito herramientas"))

    result = _run_node(_state("hola"))

    assert result == {"tool_results": []}
    assert "messages" not in result


def test_llm_cannot_choose_the_user(monkeypatch: pytest.MonkeyPatch) -> None:
    # Aunque el LLM intente pasar otro usuario, se usa siempre el del token
    other = {"user_id": "2", "nickname": "juan"}
    reply = AIMessage(content="", tool_calls=[{"name": "get_balance", "args": {"user": other}, "id": "call-1"}])
    _patch_llm(monkeypatch, reply)

    result = _run_node(_state("saldo de juan"))

    assert result == {"tool_results": [{"tool": "get_balance", "content": BALANCE_TEXT}]}


def test_user_is_hidden_from_the_llm() -> None:
    get_balance = next(tool for tool in TOOLS if tool.name == "get_balance")

    assert "user" not in get_balance.tool_call_schema.model_json_schema().get("properties", {})


def test_tool_without_user_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)

    result = _run_node(_state("cuánto tengo"), _runtime(user=None))

    assert result == {"tool_results": [{"tool": "get_balance", "content": "Error: usuario no autenticado."}]}


def test_unknown_user_has_no_account(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)

    result = _run_node(_state("cuánto tengo"), _runtime(user=CurrentUser(user_id="99", nickname="nadie")))

    assert result == {"tool_results": [{"tool": "get_balance", "content": "No se encontró una cuenta para nadie."}]}


def test_without_balance_card_emits_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    # /chat (REST) no declara la tarjeta: el texto lleva el monto y no se emite nada
    _patch_llm(monkeypatch, GET_BALANCE)
    emitted = _EmittedEvents()

    result = _run_node(_state("cuánto tengo"), emitted=emitted)

    assert emitted.events == []
    assert result == {"tool_results": [{"tool": "get_balance", "content": BALANCE_TEXT}]}


def test_emits_the_balance_card_with_the_tool_data(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)
    emitted = _EmittedEvents()

    _run_node(_state("cuánto tengo", [BALANCE_CARD_TOOL]), emitted=emitted)

    [(name, event)] = emitted.events
    assert name == MANUALLY_EMIT_TOOL_CALL
    assert event["id"].startswith("balance-")
    assert event["name"] == SHOW_ACCOUNT_BALANCE
    # Los datos salen de la tool, no del LLM
    assert event["args"] == {
        "account_number": "1001234567",
        "account_type": "Caja de ahorro",
        "currency": "BOB",
        "available": "1500.50",
    }


def test_with_balance_card_the_interpreter_does_not_get_the_amount(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)

    result = _run_node(_state("cuánto tengo", [BALANCE_CARD_TOOL]))

    [tool_result] = result["tool_results"]
    assert tool_result["tool"] == "get_balance"
    assert "tarjeta" in tool_result["content"]
    assert "****4567" in tool_result["content"]
    assert "1,500.50" not in tool_result["content"]
    assert "1001234567" not in tool_result["content"]


def test_unknown_user_with_balance_card_emits_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)
    emitted = _EmittedEvents()

    result = _run_node(
        _state("cuánto tengo", [BALANCE_CARD_TOOL]),
        _runtime(user=CurrentUser(user_id="99", nickname="nadie")),
        emitted,
    )

    assert emitted.events == []
    assert result == {"tool_results": [{"tool": "get_balance", "content": "No se encontró una cuenta para nadie."}]}


def test_balance_card_is_saved_in_the_history_with_the_same_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # Se guarda la tool call y su resultado: al volver a la sesión la tarjeta se vuelve a dibujar
    _patch_llm(monkeypatch, GET_BALANCE)
    emitted = _EmittedEvents()

    result = _run_node(_state("cuánto tengo", [BALANCE_CARD_TOOL]), emitted=emitted)

    [(_, event)] = emitted.events
    call, displayed = result["messages"]
    assert isinstance(call, AIMessage)
    assert call.tool_calls == [
        {"name": SHOW_ACCOUNT_BALANCE, "args": event["args"], "id": event["id"], "type": "tool_call"}
    ]
    assert isinstance(displayed, ToolMessage)
    assert displayed.tool_call_id == event["id"]
    assert displayed.name == SHOW_ACCOUNT_BALANCE


def test_without_balance_card_nothing_is_added_to_the_history(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, GET_BALANCE)

    result = _run_node(_state("cuánto tengo"))

    assert "messages" not in result
