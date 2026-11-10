from digital_wallet_rqm.application.ports.chat_agent import ChatAgent
from digital_wallet_rqm.application.ports.session_repository import SessionRepository
from digital_wallet_rqm.domain.models import ChatAnswer, ChatMessage, ChatSession, CurrentUser


class ChatUseCases:
    """Reglas del chat: quién puede usar cada sesión y cuándo se crea, titula o borra.

    Solo depende de puertos: no conoce FastAPI, SQLAlchemy ni LangGraph. Las operaciones que reciben al
    usuario validan la sesión: una inexistente lanza SessionNotFoundError y una de otro usuario,
    SessionForbiddenError.
    """

    def __init__(self, agent: ChatAgent, sessions: SessionRepository) -> None:
        self.agent = agent
        self.sessions = sessions

    async def create_session(self, user: CurrentUser) -> ChatSession:
        """Crea una sesión vacía; el id lo asigna el servidor"""
        return await self.sessions.create(user.user_id)

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        """Responde la pregunta; sin session_id crea una sesión nueva con id asignado por el servidor"""
        if session_id is None:
            session_id = (await self.sessions.create(user.user_id)).session_id
        else:
            await self.sessions.get_owned(user, session_id)

        response = await self.agent.answer(question, session_id, user)
        # Después del agente: si falla, la sesión no registra una actividad que no ocurrió
        await self.sessions.record_question(session_id, question)
        return ChatAnswer(session_id=session_id, response=response)

    async def list_sessions(self, user: CurrentUser) -> list[ChatSession]:
        """Devuelve las sesiones del usuario, la de actividad más reciente primero"""
        return await self.sessions.list_for_user(user.user_id)

    async def get_history(self, user: CurrentUser, session_id: str) -> list[ChatMessage]:
        """Devuelve los mensajes de la sesión en orden"""
        await self.sessions.get_owned(user, session_id)
        return await self.agent.history(session_id)

    async def delete_session(self, user: CurrentUser, session_id: str) -> None:
        """Elimina la sesión y su historial"""
        await self.sessions.get_owned(user, session_id)
        # Primero el historial y después la sesión: si falla a la mitad, la sesión sigue listada
        # y borrarla de nuevo termina el trabajo
        await self.agent.forget(session_id)
        await self.sessions.delete(session_id)

    async def start_run(self, user: CurrentUser, session_id: str) -> None:
        """Autoriza un run en streaming sobre la sesión, antes de abrir el stream"""
        await self.sessions.get_owned(user, session_id)

    async def finish_run(self, session_id: str, question: str) -> None:
        """Registra la actividad de un run que terminó bien; confía en el start_run previo"""
        await self.sessions.record_question(session_id, question)
