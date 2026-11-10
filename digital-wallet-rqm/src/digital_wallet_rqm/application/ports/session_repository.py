from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.errors import SessionForbiddenError, SessionNotFoundError
from digital_wallet_rqm.domain.models import ChatSession, CurrentUser


class SessionRepository(ABC):
    """Puerto de salida de sesiones: dueño, título y fechas de cada sesión.

    El id de una sesión nueva lo genera siempre el servidor. Los mensajes no viven aquí: los guarda
    el agente (ver ChatAgent).
    """

    @abstractmethod
    async def create(self, user_id: str) -> ChatSession:
        """Crea una sesión vacía (sin título) con un UUID nuevo"""

    @abstractmethod
    async def find(self, session_id: str) -> ChatSession | None:
        """Devuelve la sesión, o None si no existe"""

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[ChatSession]:
        """Devuelve las sesiones del usuario, la de actividad más reciente primero"""

    @abstractmethod
    async def record_question(self, session_id: str, question: str) -> None:
        """Registra actividad: pone el título con la primera pregunta y actualiza updated_at"""

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Elimina la sesión (no su historial: eso lo hace ChatAgent.forget)"""

    async def get_owned(self, user: CurrentUser, session_id: str) -> ChatSession:
        """Devuelve la sesión si es del usuario; si no existe lanza 404 y si es de otro, 403"""
        session = await self.find(session_id)
        if session is None:
            raise SessionNotFoundError()
        if session.user_id != user.user_id:
            raise SessionForbiddenError()
        return session
