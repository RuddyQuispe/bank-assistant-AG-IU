from abc import ABC, abstractmethod

from digital_wallet_rqm.domain.models import ChatMessage, CurrentUser


class ChatAgent(ABC):
    """Puerto de salida del agente conversacional: responde y guarda el historial de cada sesión.

    La aplicación no sabe que detrás hay un grafo de LangGraph: eso es un detalle del adaptador.
    """

    @abstractmethod
    async def answer(self, question: str, session_id: str, user: CurrentUser) -> str:
        """Responde la pregunta dentro de la sesión y guarda la pregunta y la respuesta en su historial"""

    @abstractmethod
    async def history(self, session_id: str) -> list[ChatMessage]:
        """Devuelve los mensajes guardados de la sesión, en orden"""

    @abstractmethod
    async def forget(self, session_id: str) -> None:
        """Borra el historial de la sesión"""
