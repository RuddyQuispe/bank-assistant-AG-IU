from abc import ABC, abstractmethod

from digital_wallet_rqm.models.current_user import CurrentUser


class SessionForbiddenError(Exception):
    """La sesión existe pero pertenece a otro usuario"""


class SessionRepository(ABC):
    """Puerto de sesiones: quién es el dueño de cada sesión (REST y AG-UI lo comparten)"""

    @abstractmethod
    async def find_owner(self, session_id: str) -> str | None:
        """Devuelve el user_id dueño de la sesión, o None si la sesión todavía no existe"""

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[str]:
        """Devuelve los id de las sesiones del usuario"""

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Elimina la sesión y su historial"""

    async def ensure_owner(self, user: CurrentUser, session_id: str) -> None:
        """Deja pasar si la sesión es nueva o del usuario; si es de otro lanza SessionForbiddenError"""
        owner = await self.find_owner(session_id)
        if owner is not None and owner != user.user_id:
            raise SessionForbiddenError(session_id)
