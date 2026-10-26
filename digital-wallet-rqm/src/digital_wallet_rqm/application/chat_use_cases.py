from digital_wallet_rqm.application.ports.inbound.chat_service import ChatService
from digital_wallet_rqm.application.ports.outbound.chat_agent import ChatAgent
from digital_wallet_rqm.application.ports.outbound.session_repository import SessionRepository
from digital_wallet_rqm.domain.models import ChatAnswer, ChatMessage, ChatSession, CurrentUser


class ChatUseCases(ChatService):
    """Reglas del chat: quién puede usar cada sesión y cuándo se crea, titula o borra.

    Solo depende de puertos: no conoce FastAPI, SQLAlchemy ni LangGraph.
    """

    def __init__(self, agent: ChatAgent, sessions: SessionRepository) -> None:
        self.agent = agent
        self.sessions = sessions

    async def create_session(self, user: CurrentUser) -> ChatSession:
        return await self.sessions.create(user.user_id)

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        if session_id is None:
            session_id = (await self.sessions.create(user.user_id)).session_id
        else:
            await self.sessions.get_owned(user, session_id)

        response = await self.agent.answer(question, session_id, user)
        # Después del agente: si falla, la sesión no registra una actividad que no ocurrió
        await self.sessions.record_question(session_id, question)
        return ChatAnswer(session_id=session_id, response=response)

    async def list_sessions(self, user: CurrentUser) -> list[ChatSession]:
        return await self.sessions.list_for_user(user.user_id)

    async def get_history(self, user: CurrentUser, session_id: str) -> list[ChatMessage]:
        await self.sessions.get_owned(user, session_id)
        return await self.agent.history(session_id)

    async def delete_session(self, user: CurrentUser, session_id: str) -> None:
        await self.sessions.get_owned(user, session_id)
        # Primero el historial y después la sesión: si falla a la mitad, la sesión sigue listada
        # y borrarla de nuevo termina el trabajo
        await self.agent.forget(session_id)
        await self.sessions.delete(session_id)
