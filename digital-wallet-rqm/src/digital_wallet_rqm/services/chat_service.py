from abc import ABC, abstractmethod
from dataclasses import dataclass

from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.models.session import ChatSession


@dataclass
class ChatAnswer:
    session_id: str
    response: str


@dataclass
class ChatMessage:
    role: str
    content: str


class ChatService(ABC):
    """Contrato del chat: la API depende de esta clase, no de LangGraph (async: la memoria es async).

    Cada operación recibe al usuario: una sesión inexistente lanza SessionNotFoundError y una
    de otro usuario, SessionForbiddenError.
    """

    @abstractmethod
    async def create_session(self, user: CurrentUser) -> ChatSession:
        """Crea una sesión vacía; el id lo asigna el servidor"""

    @abstractmethod
    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        """Responde la pregunta; sin session_id crea una sesión nueva con id asignado por el servidor"""

    @abstractmethod
    async def list_sessions(self, user: CurrentUser) -> list[ChatSession]:
        """Devuelve las sesiones del usuario, la de actividad más reciente primero"""

    @abstractmethod
    async def get_history(self, user: CurrentUser, session_id: str) -> list[ChatMessage]:
        """Devuelve los mensajes de la sesión en orden"""

    @abstractmethod
    async def delete_session(self, user: CurrentUser, session_id: str) -> None:
        """Elimina la sesión y su historial"""
