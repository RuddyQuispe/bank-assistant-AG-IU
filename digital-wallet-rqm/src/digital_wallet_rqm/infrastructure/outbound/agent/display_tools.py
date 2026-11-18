from decimal import Decimal, InvalidOperation
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage

from digital_wallet_rqm.domain.models import AccountBalance
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState

# Tools de solo mostrar: el cliente las dibuja como un componente en el chat y no devuelve resultado.
# Las emite el backend con los datos de sus tools; el LLM nunca las elige.
SHOW_ACCOUNT_BALANCE = "show_account_balance"
DISPLAY_TOOLS = frozenset({SHOW_ACCOUNT_BALANCE})

# Resultado que se guarda para cada tarjeta: deja el par tool call / resultado completo en el historial
DISPLAYED = "displayed"


def client_can_display(state: BankState, name: str) -> bool:
    """True si el cliente declaró en AG-UI que sabe dibujar ese componente (REST /chat no declara nada)"""
    return any(tool.get("name") == name for tool in state.get("tools", []))


def balance_card_args(account: AccountBalance) -> dict[str, str]:
    """Args de show_account_balance; el saldo va como texto para no perder decimales en el JSON"""
    return {
        "account_number": account.account_number,
        "account_type": account.account_type,
        "currency": account.currency,
        "available": str(account.available),
    }


def balance_from_card_args(args: dict[str, Any]) -> AccountBalance | None:
    """Vuelve a armar el saldo desde una tarjeta guardada; None si sus datos no tienen la forma esperada"""
    try:
        return AccountBalance(
            account_number=str(args["account_number"]),
            account_type=str(args["account_type"]),
            currency=str(args["currency"]),
            available=Decimal(str(args["available"])),
        )
    except (KeyError, InvalidOperation):
        return None


def display_messages(call_id: str, name: str, args: dict[str, Any]) -> list[AnyMessage]:
    """La tarjeta como tool call + su resultado, para guardarla en el checkpoint con el id que vio el navegador"""
    call = AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])
    return [call, ToolMessage(content=DISPLAYED, tool_call_id=call_id, name=name)]
