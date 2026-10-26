from abc import ABC, abstractmethod
from dataclasses import dataclass

from digital_wallet_rqm.models.current_user import CurrentUser


@dataclass
class ChatAnswer:
    session_id: str
    response: str


@dataclass
class ChatMessage:
    role: str
    content: str


class ChatService(ABC):
    """Contrato del chat: la API depende de esta clase, no de LangGraph (async: la memoria es async)"""

    @abstractmethod
    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        """Responde la pregunta del usuario; si no hay session_id crea una sesión nueva"""

    @abstractmethod
    async def list_sessions(self) -> list[str]:
        """Devuelve los id de las sesiones guardadas"""

    @abstractmethod
    async def get_history(self, session_id: str) -> list[ChatMessage]:
        """Devuelve los mensajes de la sesión en orden"""

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Elimina la sesión y su historial"""
