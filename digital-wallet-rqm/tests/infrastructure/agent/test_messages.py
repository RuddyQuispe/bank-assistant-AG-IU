from langchain_core.messages import AIMessage, HumanMessage

from digital_wallet_rqm.infrastructure.agent.messages import format_recent_context


def test_formats_last_two_messages_with_speaker() -> None:
    messages = [HumanMessage(content="viejo"), AIMessage(content="hola"), HumanMessage(content="gracias")]

    assert format_recent_context(messages) == "IA: hola\nUsuario: gracias"


def test_returns_empty_with_less_than_two_messages() -> None:
    assert format_recent_context([HumanMessage(content="hola")]) == ""
    assert format_recent_context([]) == ""


def test_skips_messages_without_content() -> None:
    messages = [AIMessage(content=""), HumanMessage(content="hola")]

    assert format_recent_context(messages) == "Usuario: hola"
