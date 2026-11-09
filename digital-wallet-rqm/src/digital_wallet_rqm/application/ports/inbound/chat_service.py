from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import ChatAnswer, ChatMessage, ChatSession, CurrentUser


class ChatService(ABC):
    """Puerto de entrada del chat: lo que la API (REST y AG-UI) le puede pedir a la aplicación.

    Las operaciones que reciben al usuario validan la sesión: una inexistente lanza SessionNotFoundError
    y una de otro usuario, SessionForbiddenError. finish_run confía en el start_run previo.
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

    @abstractmethod
    async def start_run(self, user: CurrentUser, session_id: str) -> None:
        """Autoriza un run en streaming sobre la sesión, antes de abrir el stream"""

    @abstractmethod
    async def finish_run(self, session_id: str, question: str) -> None:
        """Registra la actividad de un run que terminó bien; título con la primera pregunta"""
