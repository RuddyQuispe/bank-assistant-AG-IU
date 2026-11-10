import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableLambda

from digital_wallet_rqm.infrastructure.outbound.agent.nodes import interpreter
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interpreter import node_interpreter


class _FakeLLM:
    """Reemplaza get_llm: responde `reply` y guarda el mensaje humano que recibió"""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.human = ""

    def __call__(self, temperature: float) -> RunnableLambda[PromptValue, AIMessage]:
        return RunnableLambda(self._answer)

    def _answer(self, prompt: PromptValue) -> AIMessage:
        self.human = prompt.to_messages()[-1].text
        return AIMessage(content=self.reply, id="llm-message")


def _patch_llm(monkeypatch: pytest.MonkeyPatch, reply: str = "respuesta final") -> _FakeLLM:
    fake = _FakeLLM(reply)
    monkeypatch.setattr(interpreter, "get_llm", fake)
    return fake


def test_retrieve_route_sends_docs_with_their_source(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _patch_llm(monkeypatch)
    state = {
        "messages": [HumanMessage(content="cuánto cuesta un SPEI")],
        "question": "cuánto cuesta un SPEI",
        "route": "retrieve",
        "retrieve_docs": ["El SPEI no tiene costo."],
        "sources": [{"file": "faq.pdf", "page": 3}],
    }

    node_interpreter(state)

    assert "[faq.pdf, pág. 3] El SPEI no tiene costo." in llm.human
    assert llm.human.endswith("Pregunta: cuánto cuesta un SPEI")


def test_tools_route_sends_tool_results(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _patch_llm(monkeypatch)
    state = {
        "messages": [HumanMessage(content="cuánto tengo")],
        "question": "cuánto tengo",
        "route": "tools",
        "tool_results": [{"tool": "get_balance", "content": "Saldo disponible: 1,500.50 MXN"}],
    }

    node_interpreter(state)

    assert "get_balance: Saldo disponible: 1,500.50 MXN" in llm.human


def test_analyst_route_sends_history_without_information(monkeypatch: pytest.MonkeyPatch) -> None:
    llm = _patch_llm(monkeypatch)
    state = {
        "messages": [AIMessage(content="Tu saldo es 100"), HumanMessage(content="gracias")],
        "question": "gracias",
        "route": "analyst",
    }

    node_interpreter(state)

    assert "Historial: IA: Tu saldo es 100\nUsuario: gracias" in llm.human
    assert "Información: Ninguna (saludo o aclaración)" in llm.human


@pytest.mark.parametrize("route", ["retrieve", "tools"])
def test_empty_data_is_reported_as_unavailable(monkeypatch: pytest.MonkeyPatch, route: str) -> None:
    llm = _patch_llm(monkeypatch)
    state = {"messages": [HumanMessage(content="hola")], "question": "hola", "route": route}

    node_interpreter(state)

    assert "Información: Sin información disponible" in llm.human
    assert "Historial: Sin contexto previo" in llm.human


def test_returns_response_and_appends_it_to_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_llm(monkeypatch, reply="Tienes 1,500.50 MXN")
    state = {"messages": [HumanMessage(content="cuánto tengo")], "question": "cuánto tengo", "route": "tools"}

    result = node_interpreter(state)

    assert result == {
        "response": "Tienes 1,500.50 MXN",
        "messages": [AIMessage(content="Tienes 1,500.50 MXN", id="llm-message")],
    }


def test_appends_the_llm_message_itself_so_the_stream_id_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    # AG-UI streamea los tokens con el id del mensaje del LLM; un AIMessage nuevo tendría otro id
    _patch_llm(monkeypatch)
    state = {"messages": [HumanMessage(content="hola")], "question": "hola", "route": "analyst"}

    result = node_interpreter(state)

    assert result["messages"][0].id == "llm-message"
