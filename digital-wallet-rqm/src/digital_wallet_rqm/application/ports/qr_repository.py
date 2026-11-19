from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import QrPayment


class QrRepository(ABC):
    """Puerto de salida de los QR de cobro y de cuáles ya se pagaron"""

    @abstractmethod
    def get(self, code: str) -> QrPayment | None:
        """El QR con ese código, o None si no existe"""

    @abstractmethod
    def is_paid(self, code: str) -> bool:
        """True si el QR ya tiene un pago"""

    @abstractmethod
    def mark_paid(self, code: str) -> None:
        """Registra que el QR se pagó"""
