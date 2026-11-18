from decimal import Decimal

import pytest

from digital_wallet_rqm.domain.models import AccountBalance

ACCOUNT = AccountBalance(
    account_number="1001234567", account_type="Caja de ahorro", currency="BOB", available=Decimal("1500.50")
)


def test_masked_number_keeps_only_the_last_four_digits() -> None:
    assert ACCOUNT.masked_number == "****4567"


def test_is_immutable() -> None:
    with pytest.raises(AttributeError):
        ACCOUNT.available = Decimal("0")  # type: ignore[misc]
