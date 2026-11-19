"""Pago con QR de punta a punta en el grafo: escanear, pausar con interrupt y reanudar con la decisión"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from digital_wallet_rqm.application.qr_payment_use_cases import QrPaymentUseCases
from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import SHOW_PAYMENT_RECEIPT
from digital_wallet_rqm.infrastructure.outbound.agent.nodes import interpreter
from digital_wallet_rqm.infrastructure.outbound.agent.rag_agent import RagAgent, build_rag_agent
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import (
    DEMO_QR_EXPIRED,
    DEMO_QR_FIXED,
    DEMO_QR_OPEN,
    DemoAccountRepository,
    DemoQrRepository,
)

TODAY = date(2026, 11, 18)
NOW = datetime(2026, 11, 18, 15, 30, tzinfo=UTC)
CONFIG: RunnableConfig = {"configurable": {"thread_id": "s1"}}
TOOLS = [
    {"name": "show_qr_payment", "description": "Cobro", "parameters": {}},
    {"name": "show_payment_receipt", "description": "Comprobante", "parameters": {}},
]


class _Interpreter:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, temperature: float) -> RunnableLambda[PromptValue, AIMessage]:
        return RunnableLambda(self._answer)

    def _answer(self, prompt: PromptValue) -> AIMessage:
        self.prompts.append(prompt.to_messages()[-1].text)
        return AIMessage(content=f"respuesta {len(self.prompts)}")


@pytest.fixture
def prompts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    fake = _Interpreter()
    monkeypatch.setattr(interpreter, "get_llm", fake)
    return fake.prompts


@pytest.fixture
def accounts() -> DemoAccountRepository:
    return DemoAccountRepository()


@pytest.fixture
def context(accounts: DemoAccountRepository) -> GraphContext:
    payments = QrPaymentUseCases(
        accounts=accounts, qrs=DemoQrRepository(today=lambda: TODAY), today=lambda: TODAY, now=lambda: NOW
    )
    user = CurrentUser(user_id="1", nickname="ruddy")
    return GraphContext(vector_store=None, user=user, accounts=accounts, payments=payments)  # type: ignore[arg-type]


@pytest.fixture
def graph() -> RagAgent:
    return build_rag_agent(checkpointer=InMemorySaver())


def _scan(graph: RagAgent, context: GraphContext, code: str) -> dict[str, Any]:
    call = AIMessage(content="", tool_calls=[{"name": "scan_qr", "args": {}, "id": "scan-1"}])
    messages = [HumanMessage(content="quiero pagar con QR"), call, ToolMessage(content=code, tool_call_id="scan-1")]
    result: dict[str, Any] = graph.invoke({"messages": messages, "tools": TOOLS}, config=CONFIG, context=context)
    return result


def _resume(graph: RagAgent, context: GraphContext, decision: object) -> dict[str, Any]:
    result: dict[str, Any] = graph.invoke(Command(resume=decision), config=CONFIG, context=context)
    return result


def _balance(accounts: DemoAccountRepository, number: str) -> Decimal:
    return next(a.available for a in accounts.list_for_user("1") if a.account_number == number)


def test_scanned_qr_pauses_the_graph_waiting_for_the_payment(
    graph: RagAgent, context: GraphContext, prompts: list[str]
) -> None:
    result = _scan(graph, context, DEMO_QR_FIXED)

    # El interpreter ya respondió y el grafo quedó en pausa con el QR a pagar
    assert len(prompts) == 1
    [pause] = result["__interrupt__"]
    assert pause.value == {"type": "qr_payment", "code": DEMO_QR_FIXED}
    assert graph.get_state(CONFIG).next == ("qr_confirm",)


def test_confirmed_payment_debits_the_account_and_shows_the_receipt(
    graph: RagAgent, context: GraphContext, accounts: DemoAccountRepository, prompts: list[str]
) -> None:
    _scan(graph, context, DEMO_QR_FIXED)

    result = _resume(graph, context, {"action": "pay", "account_number": "1001234567", "amount": None})

    assert _balance(accounts, "1001234567") == Decimal("1150.50")
    assert "Pago realizado" in prompts[-1]
    assert "comprobante" in prompts[-1]
    assert "__interrupt__" not in result
    assert graph.get_state(CONFIG).next == ()
    receipts = [
        call
        for message in result["messages"]
        if isinstance(message, AIMessage)
        for call in message.tool_calls
        if call["name"] == SHOW_PAYMENT_RECEIPT
    ]
    [receipt] = receipts
    assert receipt["args"]["amount"] == "350.00"
    assert receipt["args"]["balance_after"] == "1150.50"
    assert receipt["args"]["recipient_name"] == "Juan Pérez"


def test_open_amount_qr_is_paid_with_the_amount_of_the_payer(
    graph: RagAgent, context: GraphContext, accounts: DemoAccountRepository, prompts: list[str]
) -> None:
    _scan(graph, context, DEMO_QR_OPEN)

    _resume(graph, context, {"action": "pay", "account_number": "2009876543", "amount": "25.50"})

    assert _balance(accounts, "2009876543") == Decimal("8224.50")


def test_cancelled_payment_moves_no_money(
    graph: RagAgent, context: GraphContext, accounts: DemoAccountRepository, prompts: list[str]
) -> None:
    _scan(graph, context, DEMO_QR_FIXED)

    _resume(graph, context, {"action": "cancel"})

    assert _balance(accounts, "1001234567") == Decimal("1500.50")
    assert "El cliente canceló el pago." in prompts[-1]
    assert graph.get_state(CONFIG).next == ()


def test_rejected_payment_explains_why(
    graph: RagAgent, context: GraphContext, accounts: DemoAccountRepository, prompts: list[str]
) -> None:
    _scan(graph, context, DEMO_QR_FIXED)

    _resume(graph, context, {"action": "pay", "account_number": "3005551234", "amount": None})

    assert "No se pudo pagar: La moneda de la cuenta no coincide con la del QR" in prompts[-1]
    assert _balance(accounts, "3005551234") == Decimal("320.00")


@pytest.mark.parametrize(
    "decision",
    [
        "pay",
        {"action": "steal"},
        {"action": "pay"},
        {"action": "pay", "account_number": "1001234567", "amount": "mucho"},
    ],
)
def test_malformed_decision_moves_no_money(
    graph: RagAgent, context: GraphContext, accounts: DemoAccountRepository, prompts: list[str], decision: object
) -> None:
    _scan(graph, context, DEMO_QR_FIXED)

    _resume(graph, context, decision)

    assert "No se pudo pagar: los datos del pago no son válidos." in prompts[-1]
    assert _balance(accounts, "1001234567") == Decimal("1500.50")


def test_the_qr_to_pay_comes_from_the_backend_not_from_the_decision(
    graph: RagAgent, context: GraphContext, accounts: DemoAccountRepository, prompts: list[str]
) -> None:
    # Aunque el navegador mande otro QR, se paga el que escaneó el backend
    _scan(graph, context, DEMO_QR_FIXED)

    _resume(graph, context, {"action": "pay", "account_number": "1001234567", "amount": None, "code": DEMO_QR_OPEN})

    assert _balance(accounts, "1001234567") == Decimal("1150.50")


def test_expired_qr_does_not_pause_the_graph(graph: RagAgent, context: GraphContext, prompts: list[str]) -> None:
    result = _scan(graph, context, DEMO_QR_EXPIRED)

    assert "__interrupt__" not in result
    assert graph.get_state(CONFIG).next == ()
