from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableLambda

from digital_wallet_rqm.application.qr_payment_use_cases import QrPaymentUseCases
from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import SHOW_QR_PAYMENT
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import MANUALLY_EMIT_TOOL_CALL
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.qr_payment import node_qr_payment
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import QrPaymentUpdate
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import (
    DEMO_QR_EXPIRED,
    DEMO_QR_FIXED,
    DEMO_QR_OPEN,
    DemoAccountRepository,
    DemoQrRepository,
)

TODAY = date(2026, 11, 18)
RUDDY = CurrentUser(user_id="1", nickname="ruddy")
QR_CARD_TOOL = {"name": SHOW_QR_PAYMENT, "description": "Muestra el cobro", "parameters": {}}


class _EmittedEvents(BaseCallbackHandler):
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def on_custom_event(self, name: str, data: object, **kwargs: object) -> None:
        self.events.append((name, data))


def _account(number: str, account_type: str, currency: str, available: str) -> dict[str, str]:
    return {"account_number": number, "account_type": account_type, "currency": currency, "available": available}


def _payments() -> QrPaymentUseCases:
    return QrPaymentUseCases(
        accounts=DemoAccountRepository(),
        qrs=DemoQrRepository(today=lambda: TODAY),
        today=lambda: TODAY,
        now=lambda: datetime(2026, 11, 18, 12, tzinfo=UTC),
    )


def _state(result: str, client_tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    call = AIMessage(content="", tool_calls=[{"name": "scan_qr", "args": {}, "id": "scan-1"}])
    messages = [HumanMessage(content="quiero pagar con QR"), call, ToolMessage(content=result, tool_call_id="scan-1")]
    tools = [QR_CARD_TOOL] if client_tools is None else client_tools
    return {"messages": messages, "question": "quiero pagar con QR", "tools": tools}


def _run(
    state: dict[str, Any], payments: QrPaymentUseCases | None = None, emitted: _EmittedEvents | None = None
) -> QrPaymentUpdate:
    context = GraphContext(vector_store=None, user=RUDDY, payments=payments or _payments())  # type: ignore[arg-type]
    runtime = SimpleNamespace(context=context)
    node = RunnableLambda(lambda node_state: node_qr_payment(node_state, runtime))  # type: ignore[arg-type]
    result: QrPaymentUpdate = node.invoke(state, config={"callbacks": [emitted] if emitted else []})
    return result


def test_emits_the_payment_card_with_the_qr_and_the_accounts() -> None:
    emitted = _EmittedEvents()

    _run(_state(DEMO_QR_FIXED), emitted=emitted)

    [(name, event)] = emitted.events
    assert name == MANUALLY_EMIT_TOOL_CALL
    assert event["name"] == SHOW_QR_PAYMENT
    assert event["id"].startswith("qr-")
    assert event["args"] == {
        "code": DEMO_QR_FIXED,
        "recipient_name": "Juan Pérez",
        "bank": "Banco Unión",
        "account_number": "12345678",
        "document_id": "87654321",
        "amount": "350.00",
        "currency": "BOB",
        "usage": "single",
        "expires_on": (TODAY + timedelta(days=30)).isoformat(),
        "note": "Alquiler noviembre",
        "expired": False,
        "already_paid": False,
        "accounts": [
            _account("1001234567", "Caja de ahorro", "BOB", "1500.50"),
            _account("2009876543", "Cuenta corriente", "BOB", "8250.00"),
            _account("3005551234", "Caja de ahorro", "USD", "320.00"),
        ],
    }


def test_saves_the_card_in_the_history_with_the_same_id() -> None:
    emitted = _EmittedEvents()

    update = _run(_state(DEMO_QR_FIXED), emitted=emitted)

    call, displayed = update["messages"]
    assert isinstance(call, AIMessage) and isinstance(displayed, ToolMessage)
    assert call.tool_calls[0]["id"] == emitted.events[0][1]["id"] == displayed.tool_call_id
    assert displayed.name == SHOW_QR_PAYMENT


def test_interpreter_gets_a_summary_without_repeating_the_amount() -> None:
    update = _run(_state(DEMO_QR_FIXED))

    [result] = update["tool_results"]
    assert update["route"] == "bank_tools"
    assert result["tool"] == "scan_qr"
    assert "tarjeta" in result["content"]
    assert "Juan Pérez" in result["content"]
    assert "elige la cuenta" in result["content"]
    assert "350" not in result["content"]


def test_open_amount_qr_tells_the_payer_to_set_the_amount() -> None:
    update = _run(_state(DEMO_QR_OPEN))

    assert "el cliente asigna el monto" in update["tool_results"][0]["content"]


def test_expired_qr_is_shown_but_flagged() -> None:
    emitted = _EmittedEvents()

    update = _run(_state(DEMO_QR_EXPIRED), emitted=emitted)

    assert emitted.events[0][1]["args"]["expired"] is True
    assert "vencido" in update["tool_results"][0]["content"]


def test_cancelled_scan_shows_nothing() -> None:
    emitted = _EmittedEvents()

    update = _run(_state("cancelled"), emitted=emitted)

    assert emitted.events == []
    assert "messages" not in update
    assert update["tool_results"] == [{"tool": "scan_qr", "content": "El cliente cerró el escáner sin escanear un QR."}]


def test_unknown_or_malformed_qr_is_reported() -> None:
    for code in ("qr_" + "0" * 32, "https://example.com"):
        update = _run(_state(code))

        assert update["tool_results"] == [
            {"tool": "scan_qr", "content": "El QR escaneado no es un QR de cobro válido."}
        ]


def test_without_the_card_the_interpreter_gets_the_payment_details() -> None:
    # Un cliente que no sabe dibujar la tarjeta: el texto lleva los datos
    emitted = _EmittedEvents()

    update = _run(_state(DEMO_QR_FIXED, client_tools=[]), emitted=emitted)

    assert emitted.events == []
    assert "messages" not in update
    assert "350.00 BOB" in update["tool_results"][0]["content"]


def test_without_payments_reports_it() -> None:
    state = _state(DEMO_QR_FIXED)
    runtime = SimpleNamespace(context=GraphContext(vector_store=None, user=RUDDY))  # type: ignore[arg-type]

    update = RunnableLambda(lambda s: node_qr_payment(s, runtime)).invoke(state)  # type: ignore[arg-type]

    assert update["tool_results"] == [{"tool": "scan_qr", "content": "Error: pagos no disponibles."}]
