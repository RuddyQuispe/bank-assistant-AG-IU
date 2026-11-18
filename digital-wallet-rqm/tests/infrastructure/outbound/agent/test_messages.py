from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from digital_wallet_rqm.infrastructure.outbound.agent.messages import format_recent_context, is_client_tool_result


def test_formats_last_two_messages_with_speaker() -> None:
    messages = [HumanMessage(content="viejo"), AIMessage(content="hola"), HumanMessage(content="gracias")]

    assert format_recent_context(messages) == "IA: hola\nUsuario: gracias"


def test_returns_empty_with_less_than_two_messages() -> None:
    assert format_recent_context([HumanMessage(content="hola")]) == ""
    assert format_recent_context([]) == ""


def test_skips_messages_without_content() -> None:
    messages = [AIMessage(content=""), HumanMessage(content="hola")]

    assert format_recent_context(messages) == "Usuario: hola"


def test_browser_tool_result_is_a_client_tool_result() -> None:
    result = ToolMessage(content="ok: Roboto", tool_call_id="c1", name="set_font")

    assert is_client_tool_result([HumanMessage(content="pon Roboto"), result])


def test_saved_display_card_is_not_a_client_tool_result() -> None:
    # bank_tools guarda la tarjeta con su ToolMessage: el interpreter no debe tomarlo como acción del navegador
    displayed = ToolMessage(content="displayed", tool_call_id="balance-1", name="show_account_balance")

    assert not is_client_tool_result([HumanMessage(content="cuánto tengo"), displayed])
