from dataclasses import dataclass

from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.application.ports.account_repository import AccountRepository
from digital_wallet_rqm.application.qr_payment_use_cases import QrPaymentUseCases
from digital_wallet_rqm.domain.models import CurrentUser


@dataclass(frozen=True)
class GraphContext:
    """Dependencies injected into the nodes through LangGraph's Runtime"""

    vector_store: VectorStore
    # Usuario del token; las tools lo usan para saber de quién son los datos
    user: CurrentUser | None = None
    # Cuentas del cliente; las tools las reciben del servidor, nunca del LLM
    accounts: AccountRepository | None = None
    # Pagos con QR (escanear y pagar); las reglas del pago viven en el caso de uso, no en el LLM
    payments: QrPaymentUseCases | None = None
