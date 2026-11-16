from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda

from digital_wallet_rqm.infrastructure.outbound.agent.nodes import interface
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import (
    MANUALLY_EMIT_TOOL_CALL,
    NO_CLIENT_TOOLS,
    node_interface,
)
from digital_wallet_rqm.infrastructure.outbound.agent.prompts.interface_prompt import INTERFACE_SYSTEM_PROMPT
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import InterfaceUpdate

SET_THEME = {
    "name": "set_theme",
    "description": "Cambia el tema de la app",
    "parameters": {"type": "object", "properties": {"theme": {"type": "string", "enum": ["light", "dark"]}}},
}
TOOL_CALL = AIMessage(content="", tool_calls=[{"name": "set_theme", "args": {"theme": "dark"}, "id": "call-1"}])


class _FakeLLM:
    def __init__(self, reply: AIMessage) -> None:
        self.reply = reply
        self.bound_tools: Sequence[dict[str, Any]] = []
        self.received: list[BaseMessage] = []

    def bind_tools(self, bound: Sequence[dict[str, Any]]) -> Runnable[LanguageModelInput, AIMessage]:
        self.bound_tools = bound
        return RunnableLambda(self._invoke)

    def _invoke(self, messages: list[BaseMessage]) -> AIMessage:
        self.received = messages
        return self.reply


def _patch_llm(monkeypatch: pytest.MonkeyPatch, reply: AIMessage = TOOL_CALL) -> _FakeLLM:
    fake = _FakeLLM(reply)
    monkeypatch.setattr(interface, "get_llm", lambda temperature: fake)
    return fake


def _state(question: str, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {"messages": [HumanMessage(content=question)], "question": question}
    if tools is not None:
        state["tools"] = tools
    return state


class _EmittedEvents(BaseCallbackHandler):
    """Guarda los eventos custom que emite el nodo (lo que AG-UI convierte en TOOL_CALL_*)"""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def on_custom_event(self, name: str, data: object, **kwargs: object) -> None:
        self.events.append((name, data))


def _run_node(state: dict[str, Any], emitted: _EmittedEvents | None = None) -> InterfaceUpdate:
    # Como en el grafo: el nodo corre dentro de un Runnable (necesita config para emitir eventos)
    callbacks = [emitted] if emitted else []
    result: InterfaceUpdate = RunnableLambda(node_interface).invoke(state, config={"callbacks": callbacks})
    return result


def test_binds_client_tools_and_sends_the_question(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_llm(monkeypatch)

    _run_node(_state("ponme el modo oscuro", [SET_THEME]))

    assert list(fake.bound_tools) == [SET_THEME]
    assert isinstance(fake.received[0], SystemMessage)
    assert fake.received[1:] == [HumanMessage(content="ponme el modo oscuro")]


def test_returns_the_tool_call_without_executing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch)

    update = _run_node(_state("ponme el modo oscuro", [SET_THEME]))

    # El mensaje con la tool call va al historial: AG-UI lo manda al navegador, que la ejecuta
    assert update == {"response": "", "messages": [TOOL_CALL]}


def test_without_client_tools_answers_with_fallback_text(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_llm(monkeypatch)

    update = _run_node(_state("ponme el modo oscuro"))

    # /chat no manda tools: no se llama al LLM y se explica que no se puede
    assert fake.received == []
    assert update["response"] == NO_CLIENT_TOOLS
    assert [message.text for message in update["messages"]] == [NO_CLIENT_TOOLS]


def test_emits_each_tool_call_with_its_args(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch)
    emitted = _EmittedEvents()

    _run_node(_state("ponme el modo oscuro", [SET_THEME]), emitted)

    assert emitted.events == [
        (MANUALLY_EMIT_TOOL_CALL, {"id": "call-1", "name": "set_theme", "args": {"theme": "dark"}})
    ]


def test_text_answer_without_tool_call_emits_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pide un valor que la tool no ofrece: el LLM explica las opciones en vez de llamarla
    reply = AIMessage(content="Solo tengo las fuentes Inter y Roboto.")
    _patch_llm(monkeypatch, reply)
    emitted = _EmittedEvents()

    update = _run_node(_state("pon Comic Sans", [SET_THEME]), emitted)

    assert emitted.events == []
    assert update == {"response": "Solo tengo las fuentes Inter y Roboto.", "messages": [reply]}


def test_tool_call_without_id_gets_one_shared_by_event_and_history(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = AIMessage(content="", tool_calls=[{"name": "set_theme", "args": {"theme": "dark"}, "id": None}])
    _patch_llm(monkeypatch, reply)
    emitted = _EmittedEvents()

    update = _run_node(_state("ponme el modo oscuro", [SET_THEME]), emitted)

    # El navegador usa el id para devolver el resultado: debe existir y coincidir con el historial
    event_id = emitted.events[0][1]["id"]
    assert event_id
    assert update["messages"][0].tool_calls[0]["id"] == event_id


def test_prompt_covers_everything_the_analyzer_routes_here() -> None:
    for topic in ("claro u oscuro", "color puro o degradado", "tipo de letra", "tamaño de letra"):
        assert topic in INTERFACE_SYSTEM_PROMPT


def test_prompt_asks_to_turn_color_names_into_css_colors() -> None:
    assert "conviértelo tú a hex o rgb/rgba" in INTERFACE_SYSTEM_PROMPT
