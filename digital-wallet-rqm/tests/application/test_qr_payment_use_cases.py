from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from digital_wallet_rqm.application.ports.account_repository import AccountRepository
from digital_wallet_rqm.application.ports.qr_repository import QrRepository
from digital_wallet_rqm.application.qr_payment_use_cases import QrPaymentUseCases
from digital_wallet_rqm.domain.errors import (
    AccountNotFoundError,
    CurrencyMismatchError,
    InsufficientFundsError,
    InvalidPaymentAmountError,
    QrAlreadyPaidError,
    QrExpiredError,
    QrNotFoundError,
)
from digital_wallet_rqm.domain.models import AccountBalance, Bank, CurrentUser, QrPayment, QrUsage

TODAY = date(2026, 11, 17)
# Los QR solo llevan un token opaco: "qr_" + 32 hex
FIXED_CODE = "qr_" + "a" * 32
OPEN_CODE = "qr_" + "b" * 32
EXPIRED_CODE = "qr_" + "c" * 32
UNKNOWN_CODE = "qr_" + "d" * 32
NOW = datetime(2026, 11, 17, 15, 30, tzinfo=UTC)
RUDDY = CurrentUser(user_id="1", nickname="ruddy")
JUAN = CurrentUser(user_id="2", nickname="juan")

SAVINGS = AccountBalance("1001234567", "Caja de ahorro", "BOB", Decimal("1500.50"))
CHECKING = AccountBalance("2009876543", "Cuenta corriente", "BOB", Decimal("100.00"))
DOLLARS = AccountBalance("3005551234", "Caja de ahorro", "USD", Decimal("320.00"))

FIXED = QrPayment(
    code=FIXED_CODE,
    recipient_name="Juan Pérez",
    bank=Bank.UNION,
    account_number="12345678",
    document_id="87654321",
    amount=Decimal("350.00"),
    currency="BOB",
    usage=QrUsage.SINGLE,
    expires_on=TODAY,
    note="Alquiler noviembre",
)
OPEN = replace(FIXED, code=OPEN_CODE, amount=Decimal("0"), usage=QrUsage.MULTIPLE, recipient_name="Tienda Rosa")
EXPIRED = replace(FIXED, code=EXPIRED_CODE, expires_on=date(2026, 11, 16))


class InMemoryAccounts(AccountRepository):
    def __init__(self) -> None:
        self.accounts = {"1": [SAVINGS, CHECKING, DOLLARS]}

    def list_for_user(self, user_id: str) -> list[AccountBalance]:
        return list(self.accounts.get(user_id, []))

    def save(self, user_id: str, account: AccountBalance) -> None:
        self.accounts[user_id] = [
            account if current.account_number == account.account_number else current
            for current in self.accounts[user_id]
        ]

    def balance(self, account_number: str) -> Decimal:
        return next(a.available for a in self.accounts["1"] if a.account_number == account_number)


class InMemoryQrs(QrRepository):
    def __init__(self) -> None:
        self.qrs = {qr.code: qr for qr in (FIXED, OPEN, EXPIRED)}
        self.paid: set[str] = set()

    def get(self, code: str) -> QrPayment | None:
        return self.qrs.get(code)

    def is_paid(self, code: str) -> bool:
        return code in self.paid

    def mark_paid(self, code: str) -> None:
        self.paid.add(code)


@pytest.fixture
def accounts() -> InMemoryAccounts:
    return InMemoryAccounts()


@pytest.fixture
def qrs() -> InMemoryQrs:
    return InMemoryQrs()


@pytest.fixture
def payments(accounts: InMemoryAccounts, qrs: InMemoryQrs) -> QrPaymentUseCases:
    return QrPaymentUseCases(accounts=accounts, qrs=qrs, today=lambda: TODAY, now=lambda: NOW)


# --- scan ---


def test_scan_returns_the_qr_and_the_accounts_of_the_user(payments: QrPaymentUseCases) -> None:
    scan = payments.scan(RUDDY, FIXED_CODE)

    assert scan.qr == FIXED
    assert scan.accounts == [SAVINGS, CHECKING, DOLLARS]
    assert not scan.expired
    assert not scan.already_paid


def test_scan_flags_an_expired_qr_instead_of_failing(payments: QrPaymentUseCases) -> None:
    # La tarjeta muestra el aviso de vencido: el escaneo no falla
    assert payments.scan(RUDDY, EXPIRED_CODE).expired


def test_scan_flags_a_single_use_qr_already_paid(payments: QrPaymentUseCases, qrs: InMemoryQrs) -> None:
    qrs.paid.add(FIXED_CODE)

    assert payments.scan(RUDDY, FIXED_CODE).already_paid


def test_scan_of_an_unknown_qr_fails(payments: QrPaymentUseCases) -> None:
    with pytest.raises(QrNotFoundError):
        payments.scan(RUDDY, UNKNOWN_CODE)


@pytest.mark.parametrize("code", ["QR-DEMO-001", "qr_ABC", "qr_" + "g" * 32, "qr_" + "a" * 33, " qr_" + "a" * 32, ""])
def test_scan_rejects_a_code_that_is_not_a_qr_token(payments: QrPaymentUseCases, qrs: InMemoryQrs, code: str) -> None:
    # Aunque existiera un QR con ese código, lo que no tiene forma de token no se busca
    qrs.qrs[code] = replace(FIXED, code=code)

    with pytest.raises(QrNotFoundError):
        payments.scan(RUDDY, code)


# --- pay ---


def test_pay_a_fixed_amount_qr_debits_the_account_and_returns_the_receipt(
    payments: QrPaymentUseCases, accounts: InMemoryAccounts, qrs: InMemoryQrs
) -> None:
    receipt = payments.pay(RUDDY, FIXED_CODE, account_number="1001234567", amount=None)

    assert receipt.qr_code == FIXED_CODE
    assert receipt.amount == Decimal("350.00")
    assert receipt.currency == "BOB"
    assert receipt.recipient_name == "Juan Pérez"
    assert receipt.bank == Bank.UNION
    assert receipt.destination_account == "12345678"
    assert receipt.from_account == SAVINGS.account_number
    assert receipt.balance_after == Decimal("1150.50")
    assert receipt.paid_at == NOW
    assert receipt.receipt_number.startswith("PAY-")
    assert accounts.balance("1001234567") == Decimal("1150.50")
    assert qrs.is_paid(FIXED_CODE)


def test_fixed_amount_accepts_the_same_amount_from_the_payer(payments: QrPaymentUseCases) -> None:
    receipt = payments.pay(RUDDY, FIXED_CODE, account_number="1001234567", amount=Decimal("350"))

    assert receipt.amount == Decimal("350.00")


def test_fixed_amount_rejects_a_different_amount(payments: QrPaymentUseCases, accounts: InMemoryAccounts) -> None:
    with pytest.raises(InvalidPaymentAmountError):
        payments.pay(RUDDY, FIXED_CODE, account_number="1001234567", amount=Decimal("10"))

    assert accounts.balance("1001234567") == Decimal("1500.50")


def test_single_use_qr_cannot_be_paid_twice(payments: QrPaymentUseCases, accounts: InMemoryAccounts) -> None:
    payments.pay(RUDDY, FIXED_CODE, account_number="1001234567", amount=None)

    with pytest.raises(QrAlreadyPaidError):
        payments.pay(RUDDY, FIXED_CODE, account_number="1001234567", amount=None)
    assert accounts.balance("1001234567") == Decimal("1150.50")


def test_multiple_use_qr_can_be_paid_again(payments: QrPaymentUseCases, accounts: InMemoryAccounts) -> None:
    payments.pay(RUDDY, OPEN_CODE, account_number="1001234567", amount=Decimal("20"))
    payments.pay(RUDDY, OPEN_CODE, account_number="1001234567", amount=Decimal("30.25"))

    assert accounts.balance("1001234567") == Decimal("1450.25")


def test_expired_qr_cannot_be_paid(payments: QrPaymentUseCases, accounts: InMemoryAccounts) -> None:
    with pytest.raises(QrExpiredError):
        payments.pay(RUDDY, EXPIRED_CODE, account_number="1001234567", amount=None)

    assert accounts.balance("1001234567") == Decimal("1500.50")


@pytest.mark.parametrize("amount", [None, Decimal("0"), Decimal("-5"), Decimal("10.001")])
def test_open_amount_qr_needs_a_positive_amount_with_cents(payments: QrPaymentUseCases, amount: Decimal | None) -> None:
    with pytest.raises(InvalidPaymentAmountError):
        payments.pay(RUDDY, OPEN_CODE, account_number="1001234567", amount=amount)


def test_insufficient_funds_changes_nothing(
    payments: QrPaymentUseCases, accounts: InMemoryAccounts, qrs: InMemoryQrs
) -> None:
    with pytest.raises(InsufficientFundsError):
        payments.pay(RUDDY, FIXED_CODE, account_number="2009876543", amount=None)

    assert accounts.balance("2009876543") == Decimal("100.00")
    assert not qrs.is_paid(FIXED_CODE)


def test_account_currency_must_match_the_qr(payments: QrPaymentUseCases) -> None:
    with pytest.raises(CurrencyMismatchError):
        payments.pay(RUDDY, FIXED_CODE, account_number="3005551234", amount=None)


def test_cannot_pay_from_an_account_of_another_user(payments: QrPaymentUseCases) -> None:
    with pytest.raises(AccountNotFoundError):
        payments.pay(JUAN, FIXED_CODE, account_number="1001234567", amount=None)


def test_pay_an_unknown_qr_fails(payments: QrPaymentUseCases) -> None:
    with pytest.raises(QrNotFoundError):
        payments.pay(RUDDY, UNKNOWN_CODE, account_number="1001234567", amount=None)


def test_concurrent_payments_of_a_single_use_qr_charge_only_once(
    payments: QrPaymentUseCases, accounts: InMemoryAccounts
) -> None:
    def pay() -> str:
        try:
            payments.pay(RUDDY, FIXED_CODE, account_number="1001234567", amount=None)
            return "paid"
        except QrAlreadyPaidError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: pay(), range(8)))

    assert results.count("paid") == 1
    assert accounts.balance("1001234567") == Decimal("1150.50")
