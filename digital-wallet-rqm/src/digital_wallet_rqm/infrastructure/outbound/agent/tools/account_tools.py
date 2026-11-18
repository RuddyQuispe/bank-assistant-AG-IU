from decimal import Decimal
from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool

from digital_wallet_rqm.domain.models import AccountBalance, CurrentUser

# Cuentas de prueba por user_id, mientras no exista una base de cuentas
_DEMO_ACCOUNTS = {
    "1": AccountBalance(
        account_number="1001234567", account_type="Caja de ahorro", currency="BOB", available=Decimal("1500.50")
    ),
}
# Cómo se escribe cada moneda en el texto para el cliente
_CURRENCY_LABELS = {"BOB": "Bs", "USD": "USD"}


# content_and_artifact: el texto va al LLM y el AccountBalance queda en ToolMessage.artifact para la tarjeta
@tool(response_format="content_and_artifact")
def get_balance(user: Annotated[CurrentUser, InjectedToolArg]) -> tuple[str, AccountBalance | None]:
    """Devuelve el saldo disponible de la cuenta del cliente."""
    # "user" lo pone el servidor desde el token: InjectedToolArg lo oculta al LLM
    account = _DEMO_ACCOUNTS.get(user.user_id)
    if account is None:
        return f"No se encontró una cuenta para {user.nickname}.", None
    currency = _CURRENCY_LABELS.get(account.currency, account.currency)
    text = (
        f"Saldo disponible de {user.nickname} en {account.account_type} {account.masked_number}: "
        f"{account.available:,.2f} {currency}"
    )
    return text, account
