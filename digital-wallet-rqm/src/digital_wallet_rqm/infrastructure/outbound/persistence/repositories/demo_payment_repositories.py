from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from threading import Lock

from digital_wallet_rqm.application.ports.account_repository import AccountRepository
from digital_wallet_rqm.application.ports.qr_repository import QrRepository
from digital_wallet_rqm.domain.models import AccountBalance, Bank, QrPayment, QrUsage
from digital_wallet_rqm.infrastructure.settings import settings

# Tokens fijos de los QR de prueba: no cambian entre reinicios, así un PNG descargado sigue sirviendo
DEMO_QR_FIXED = "qr_af9bd6ff81dc2525a2fba110bf390946"
DEMO_QR_OPEN = "qr_3b36a52a2156ca40e23ad69a5a7cfc59"
DEMO_QR_EXPIRED = "qr_df40d18b8b020fd1980aea44c57f51eb"


def _demo_accounts() -> dict[str, list[AccountBalance]]:
    # Cuentas de prueba del usuario demo; la primera es la principal (la que muestra get_balance)
    return {
        settings.DEMO_USER_ID: [
            AccountBalance("1001234567", "Caja de ahorro", "BOB", Decimal("1500.50")),
            AccountBalance("2009876543", "Cuenta corriente", "BOB", Decimal("8250.00")),
            AccountBalance("3005551234", "Caja de ahorro", "USD", Decimal("320.00")),
        ],
    }


class DemoAccountRepository(AccountRepository):
    """Cuentas de prueba en memoria: los pagos descuentan el saldo y todo vuelve al inicio al reiniciar"""

    def __init__(self) -> None:
        self._accounts = _demo_accounts()
        self._lock = Lock()

    def list_for_user(self, user_id: str) -> list[AccountBalance]:
        with self._lock:
            return list(self._accounts.get(user_id, []))

    def save(self, user_id: str, account: AccountBalance) -> None:
        with self._lock:
            self._accounts[user_id] = [
                account if current.account_number == account.account_number else current
                for current in self._accounts.get(user_id, [])
            ]


class DemoQrRepository(QrRepository):
    """QRs de prueba: monto fijo de pago único, monto libre de pagos múltiples y uno vencido.

    Los vencimientos se calculan desde hoy, así los datos de prueba no caducan solos.
    """

    def __init__(self, today: Callable[[], date]) -> None:
        start = today()
        qrs = [
            QrPayment(
                code=DEMO_QR_FIXED,
                recipient_name="Juan Pérez",
                bank=Bank.UNION,
                account_number="12345678",
                document_id="87654321",
                amount=Decimal("350.00"),
                currency="BOB",
                usage=QrUsage.SINGLE,
                expires_on=start + timedelta(days=30),
                note="Alquiler noviembre",
            ),
            QrPayment(
                code=DEMO_QR_OPEN,
                recipient_name="Tienda Doña Rosa",
                bank=Bank.GANADERO,
                account_number="23456789",
                document_id="76543210",
                amount=Decimal("0"),
                currency="BOB",
                usage=QrUsage.MULTIPLE,
                expires_on=start + timedelta(days=90),
                note="Pago de compras",
            ),
            QrPayment(
                code=DEMO_QR_EXPIRED,
                recipient_name="Club Deportivo Andino",
                bank=Bank.BISA,
                account_number="34567890",
                document_id="65432109",
                amount=Decimal("120.00"),
                currency="BOB",
                usage=QrUsage.SINGLE,
                expires_on=start - timedelta(days=1),
                note="Cuota mensual",
            ),
        ]
        self._qrs = {qr.code: qr for qr in qrs}
        self._paid: set[str] = set()
        self._lock = Lock()

    def codes(self) -> list[str]:
        """Tokens de los QR de prueba, para dibujarlos en el escáner simulado (solo demo)"""
        return list(self._qrs)

    def get(self, code: str) -> QrPayment | None:
        return self._qrs.get(code)

    def is_paid(self, code: str) -> bool:
        with self._lock:
            return code in self._paid

    def mark_paid(self, code: str) -> None:
        with self._lock:
            self._paid.add(code)
