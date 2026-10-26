from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from digital_wallet_rqm.infrastructure.agent.nodes import analyzer
from digital_wallet_rqm.infrastructure.agent.nodes.analyzer import node_analyzer
from digital_wallet_rqm.infrastructure.agent.route_decision import RouteDecision


def _state(question: str) -> dict:
    return {"messages": [], "question": question}


def _patch_llm(monkeypatch, result):
    captured = {}

    def fake_get_llm(temperature, response_format=None):
        captured["response_format"] = response_format
        return RunnableLambda(lambda _: result)

    monkeypatch.setattr(analyzer, "get_llm", fake_get_llm)
    return captured


def test_returns_route_from_structured_output(monkeypatch):
    captured = _patch_llm(monkeypatch, RouteDecision(route="tools", reason="saldo"))

    assert node_analyzer(_state("cuánto tengo")) == {"route": "tools"}
    assert captured["response_format"] is RouteDecision


def test_falls_back_to_retrieve_when_output_is_none(monkeypatch):
    _patch_llm(monkeypatch, None)

    assert node_analyzer(_state("???")) == {"route": "retrieve"}


def test_sends_last_two_messages_as_context(monkeypatch):
    received = {}

    def fake_get_llm(temperature, response_format=None):
        def _capture(prompt):
            received["human"] = prompt.to_messages()[-1].content
            return RouteDecision(route="tools", reason="seguimiento")

        return RunnableLambda(_capture)

    monkeypatch.setattr(analyzer, "get_llm", fake_get_llm)
    state = {
        "messages": [
            HumanMessage(content="viejo"),
            AIMessage(content="Tu saldo es 100"),
            HumanMessage(content="y en dólares?"),
        ],
        "question": "y en dólares?",
    }

    node_analyzer(state)

    assert received["human"] == "Contexto previo: IA: Tu saldo es 100\nUsuario: y en dólares?\nMensaje: y en dólares?"
