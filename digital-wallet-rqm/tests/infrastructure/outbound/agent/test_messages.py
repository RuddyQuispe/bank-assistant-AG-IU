from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from digital_wallet_rqm.infrastructure.outbound.agent.messages import (
    format_recent_context,
    is_client_tool_result,
    scanned_qr,
)


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


def _scan_turn(result: str) -> list[BaseMessage]:
    call = AIMessage(content="", tool_calls=[{"name": "scan_qr", "args": {}, "id": "scan-1"}])
    return [HumanMessage(content="quiero pagar con QR"), call, ToolMessage(content=result, tool_call_id="scan-1")]


def test_scanned_qr_returns_the_result_of_scan_qr() -> None:
    assert scanned_qr(_scan_turn("qr_" + "a" * 32)) == "qr_" + "a" * 32
    assert scanned_qr(_scan_turn("cancelled")) == "cancelled"


def test_scanned_qr_is_none_for_other_tool_results() -> None:
    call = AIMessage(content="", tool_calls=[{"name": "set_font", "args": {}, "id": "c1"}])
    messages = [HumanMessage(content="pon Roboto"), call, ToolMessage(content="ok: Roboto", tool_call_id="c1")]

    assert scanned_qr(messages) is None
    assert scanned_qr([HumanMessage(content="hola")]) is None


def test_scan_result_is_handled_by_the_backend_not_confirmed_as_a_browser_action() -> None:
    # El escaneo no es una acción ya aplicada: el backend busca el QR (nodo qr_payment)
    assert not is_client_tool_result(_scan_turn("qr_" + "a" * 32))
