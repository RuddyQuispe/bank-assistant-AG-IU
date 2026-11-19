from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from threading import Lock
from uuid import uuid4

from digital_wallet_rqm.application.ports.account_repository import AccountRepository
from digital_wallet_rqm.application.ports.qr_repository import QrRepository
from digital_wallet_rqm.domain.errors import (
    AccountNotFoundError,
    CurrencyMismatchError,
    InsufficientFundsError,
    InvalidPaymentAmountError,
    QrAlreadyPaidError,
    QrExpiredError,
    QrNotFoundError,
)
from digital_wallet_rqm.domain.models import (
    AccountBalance,
    CurrentUser,
    PaymentReceipt,
    QrPayment,
    QrScan,
    QrUsage,
    is_qr_token,
)

_CENTS = Decimal("0.01")


class QrPaymentUseCases:
    """Escanear un QR de cobro y pagarlo desde una cuenta del cliente.

    Todas las reglas del pago viven acá: el LLM nunca decide si se mueve plata.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        qrs: QrRepository,
        today: Callable[[], date],
        now: Callable[[], datetime],
    ) -> None:
        self.accounts = accounts
        self.qrs = qrs
        self.today = today
        self.now = now
        # Un pago a la vez: validar y descontar no se pueden intercalar con otro pago
        self._lock = Lock()

    def scan(self, user: CurrentUser, code: str) -> QrScan:
        """Datos del QR y cuentas del usuario; un QR vencido o pagado se marca, no falla"""
        qr = self._get_qr(code)
        return QrScan(
            qr=qr,
            accounts=self.accounts.list_for_user(user.user_id),
            expired=qr.is_expired(self.today()),
            already_paid=qr.usage == QrUsage.SINGLE and self.qrs.is_paid(code),
        )

    def pay(self, user: CurrentUser, code: str, account_number: str, amount: Decimal | None) -> PaymentReceipt:
        """Paga el QR desde la cuenta elegida; amount solo hace falta si el QR tiene monto 0"""
        with self._lock:
            # 1. El QR existe, está vigente y, si es de pago único, no se pagó
            qr = self._get_qr(code)
            if qr.is_expired(self.today()):
                raise QrExpiredError()
            if qr.usage == QrUsage.SINGLE and self.qrs.is_paid(code):
                raise QrAlreadyPaidError()

            # 2. La cuenta es del usuario y de la misma moneda
            account = self._get_account(user, account_number)
            if account.currency != qr.currency:
                raise CurrencyMismatchError()

            # 3. Monto: el del QR, o el del pagador si el QR viene en 0
            to_pay = _amount_to_pay(qr, amount)
            if account.available < to_pay:
                raise InsufficientFundsError()

            # 4. Descuenta, registra el pago y arma el comprobante
            debited = replace(account, available=account.available - to_pay)
            self.accounts.save(user.user_id, debited)
            self.qrs.mark_paid(code)
            return PaymentReceipt(
                receipt_number=f"PAY-{uuid4().hex[:10].upper()}",
                qr_code=qr.code,
                recipient_name=qr.recipient_name,
                bank=qr.bank,
                destination_account=qr.account_number,
                from_account=account.account_number,
                amount=to_pay,
                currency=qr.currency,
                balance_after=debited.available,
                paid_at=self.now(),
            )

    def _get_qr(self, code: str) -> QrPayment:
        # Lo que no tiene forma de token no se busca: llega del navegador (imagen subida, cámara)
        qr = self.qrs.get(code) if is_qr_token(code) else None
        if qr is None:
            raise QrNotFoundError()
        return qr

    def _get_account(self, user: CurrentUser, account_number: str) -> AccountBalance:
        for account in self.accounts.list_for_user(user.user_id):
            if account.account_number == account_number:
                return account
        raise AccountNotFoundError()


def _amount_to_pay(qr: QrPayment, amount: Decimal | None) -> Decimal:
    """Monto fijo del QR (el pagador puede repetirlo) o el que asigna el pagador, positivo y con centavos"""
    if not qr.payer_sets_amount:
        if amount is not None and amount != qr.amount:
            raise InvalidPaymentAmountError(f"El QR tiene un monto fijo de {qr.amount:,.2f} {qr.currency}")
        return qr.amount
    # NaN e Infinity se descartan primero: compararlos o redondearlos lanza InvalidOperation
    if amount is None or not amount.is_finite() or amount <= 0 or amount != amount.quantize(_CENTS):
        raise InvalidPaymentAmountError()
    return amount
