from typing import Annotated

from langchain_core.tools import InjectedToolArg, tool

from digital_wallet_rqm.domain.models.current_user import CurrentUser

# Saldos de prueba por user_id, mientras no exista una base de cuentas
_DEMO_BALANCES = {"1": "1,500.50 Bs"}


@tool
def get_balance(user: Annotated[CurrentUser, InjectedToolArg]) -> str:
    """Devuelve el saldo disponible de la cuenta del cliente."""
    # "user" lo pone el servidor desde el token: InjectedToolArg lo oculta al LLM
    balance = _DEMO_BALANCES.get(user.user_id)
    if balance is None:
        return f"No se encontró una cuenta para {user.nickname}."
    return f"Saldo disponible de {user.nickname}: {balance}"
