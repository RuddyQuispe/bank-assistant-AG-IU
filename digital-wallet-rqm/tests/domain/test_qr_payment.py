from datetime import date
from decimal import Decimal

import pytest

from digital_wallet_rqm.domain.models import Bank, QrPayment, QrUsage, is_qr_token

TODAY = date(2026, 11, 17)


def _qr(**changes: object) -> QrPayment:
    data: dict[str, object] = {
        "code": "QR-1",
        "recipient_name": "Juan Pérez",
        "bank": Bank.UNION,
        "account_number": "12345678",
        "document_id": "87654321",
        "amount": Decimal("350.00"),
        "currency": "BOB",
        "usage": QrUsage.SINGLE,
        "expires_on": TODAY,
        "note": "Alquiler noviembre",
    }
    return QrPayment(**{**data, **changes})  # type: ignore[arg-type]


def test_banks_offered_for_the_destination() -> None:
    assert [bank.value for bank in Bank] == [
        "Banco Unión",
        "Banco Económico",
        "Banco Ganadero",
        "Banco BISA",
        "Banco Mercantil Santa Cruz",
    ]


def test_qr_is_valid_until_the_end_of_its_expiry_day() -> None:
    assert not _qr(expires_on=TODAY).is_expired(TODAY)
    assert _qr(expires_on=date(2026, 11, 16)).is_expired(TODAY)


def test_payer_sets_the_amount_when_the_qr_amount_is_zero() -> None:
    assert _qr(amount=Decimal("0")).payer_sets_amount
    assert not _qr().payer_sets_amount


@pytest.mark.parametrize(
    "changes",
    [
        {"account_number": "1234567"},
        {"account_number": "1234567a"},
        {"document_id": "123456789"},
        {"amount": Decimal("-1")},
    ],
)
def test_rejects_invalid_qr_data(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _qr(**changes)


def test_qr_token_is_qr_prefix_and_32_hex_chars() -> None:
    assert is_qr_token("qr_af9bd6ff81dc2525a2fba110bf390946")
    assert not is_qr_token("QR-DEMO-001")
    assert not is_qr_token("qr_AF9BD6FF81DC2525A2FBA110BF390946")
    assert not is_qr_token("qr_af9bd6ff81dc2525a2fba110bf39094")
