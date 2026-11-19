from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool

from digital_wallet_rqm.application.ports.account_repository import AccountRepository
from digital_wallet_rqm.domain.models import AccountBalance, CurrentUser

# Cómo se escribe cada moneda en el texto para el cliente
_CURRENCY_LABELS = {"BOB": "Bs", "USD": "USD"}


# content_and_artifact: el texto va al LLM y el AccountBalance queda en ToolMessage.artifact para la tarjeta
@tool(response_format="content_and_artifact")
def get_balance(
    user: Annotated[CurrentUser, InjectedToolArg],
    accounts: Annotated[AccountRepository, InjectedToolArg],
) -> tuple[str, AccountBalance | None]:
    """Devuelve el saldo disponible de la cuenta del cliente."""
    # "user" y "accounts" los pone el servidor: InjectedToolArg los oculta al LLM
    # La cuenta principal es la primera del cliente
    account = next(iter(accounts.list_for_user(user.user_id)), None)
    if account is None:
        return f"No se encontró una cuenta para {user.nickname}.", None
    currency = _CURRENCY_LABELS.get(account.currency, account.currency)
    text = (
        f"Saldo disponible de {user.nickname} en {account.account_type} {account.masked_number}: "
        f"{account.available:,.2f} {currency}"
    )
    return text, account
