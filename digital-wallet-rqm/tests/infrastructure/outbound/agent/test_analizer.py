from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from digital_wallet_rqm.infrastructure.outbound.agent.nodes import analyzer
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.analyzer import node_analyzer
from digital_wallet_rqm.infrastructure.outbound.agent.route_decision import RouteDecision


def _state(question: str) -> dict:
    return {"messages": [], "question": question}


class _FakeLLM:
    """Reemplaza get_llm: responde siempre `reply` y guarda lo que recibió"""

    def __init__(self, reply):
        self.reply = reply
        self.response_format = None
        self.human = None

    def __call__(self, temperature, response_format=None):
        self.response_format = response_format
        return RunnableLambda(self._answer)

    def _answer(self, prompt):
        self.human = prompt.to_messages()[-1].content
        return self.reply


def _patch_llm(monkeypatch, reply):
    fake = _FakeLLM(reply)
    monkeypatch.setattr(analyzer, "get_llm", fake)
    return fake


def test_returns_route_from_structured_output(monkeypatch):
    llm = _patch_llm(monkeypatch, RouteDecision(route="tools", reason="saldo"))

    assert node_analyzer(_state("cuánto tengo")) == {"route": "tools"}
    assert llm.response_format is RouteDecision


def test_falls_back_to_retrieve_when_output_is_none(monkeypatch):
    _patch_llm(monkeypatch, None)

    assert node_analyzer(_state("???")) == {"route": "retrieve"}


def test_sends_last_two_messages_as_context(monkeypatch):
    llm = _patch_llm(monkeypatch, RouteDecision(route="tools", reason="seguimiento"))
    state = {
        "messages": [
            HumanMessage(content="viejo"),
            AIMessage(content="Tu saldo es 100"),
            HumanMessage(content="y en dólares?"),
        ],
        "question": "y en dólares?",
    }

    node_analyzer(state)

    assert llm.human == "Contexto previo: IA: Tu saldo es 100\nUsuario: y en dólares?\nMensaje: y en dólares?"
