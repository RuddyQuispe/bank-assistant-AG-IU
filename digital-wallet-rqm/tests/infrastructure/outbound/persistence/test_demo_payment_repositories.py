from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from digital_wallet_rqm.domain.models import QrUsage, is_qr_token
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import (
    DEMO_QR_EXPIRED,
    DEMO_QR_FIXED,
    DEMO_QR_OPEN,
    DemoAccountRepository,
    DemoQrRepository,
)

TODAY = date(2026, 11, 17)


def test_ruddy_has_three_accounts_to_pay_from() -> None:
    accounts = DemoAccountRepository().list_for_user("1")

    assert [(a.account_number, a.account_type, a.currency, a.available) for a in accounts] == [
        ("1001234567", "Caja de ahorro", "BOB", Decimal("1500.50")),
        ("2009876543", "Cuenta corriente", "BOB", Decimal("8250.00")),
        ("3005551234", "Caja de ahorro", "USD", Decimal("320.00")),
    ]


def test_other_users_have_no_accounts() -> None:
    assert DemoAccountRepository().list_for_user("99") == []


def test_save_updates_the_balance_of_that_account_only() -> None:
    repository = DemoAccountRepository()
    savings = repository.list_for_user("1")[0]

    repository.save("1", replace(savings, available=Decimal("10.00")))

    balances = [account.available for account in repository.list_for_user("1")]
    assert balances == [Decimal("10.00"), Decimal("8250.00"), Decimal("320.00")]


def test_each_repository_starts_with_its_own_balances() -> None:
    # Los pagos de una instancia no tocan los datos de prueba de otra
    first = DemoAccountRepository()
    first.save("1", replace(first.list_for_user("1")[0], available=Decimal("0")))

    assert DemoAccountRepository().list_for_user("1")[0].available == Decimal("1500.50")


def test_demo_qrs_cover_fixed_open_and_expired() -> None:
    repository = DemoQrRepository(today=lambda: TODAY)

    fixed = repository.get(DEMO_QR_FIXED)
    open_amount = repository.get(DEMO_QR_OPEN)
    expired = repository.get(DEMO_QR_EXPIRED)

    assert fixed is not None and fixed.usage == QrUsage.SINGLE and fixed.amount > 0
    assert not fixed.is_expired(TODAY)
    assert open_amount is not None and open_amount.usage == QrUsage.MULTIPLE and open_amount.payer_sets_amount
    assert expired is not None and expired.is_expired(TODAY)
    assert expired.expires_on == TODAY - timedelta(days=1)
    assert repository.get("qr_" + "0" * 32) is None


def test_mark_paid() -> None:
    repository = DemoQrRepository(today=lambda: TODAY)

    repository.mark_paid(DEMO_QR_FIXED)

    assert repository.is_paid(DEMO_QR_FIXED)
    assert not repository.is_paid(DEMO_QR_OPEN)


def test_demo_codes_are_opaque_tokens_in_a_stable_order() -> None:
    # Fijos entre reinicios: un PNG descargado sigue sirviendo
    repository = DemoQrRepository(today=lambda: TODAY)

    assert repository.codes() == [DEMO_QR_FIXED, DEMO_QR_OPEN, DEMO_QR_EXPIRED]
    assert all(is_qr_token(code) for code in repository.codes())
