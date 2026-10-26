from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.rag_agent import RagAgent
from digital_wallet_rqm.memory import checkpointer as memory
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.models.session import ChatSession
from digital_wallet_rqm.services.chat_service import ChatAnswer, ChatMessage, ChatService
from digital_wallet_rqm.services.session_repository import SessionRepository


class LangGraphChatService(ChatService):
    """Implementación del chat usando el agente RAG de LangGraph"""

    def __init__(self, agent: RagAgent, sessions: SessionRepository, vector_store: VectorStore) -> None:
        self.agent = agent
        self.sessions = sessions
        self.vector_store = vector_store

    async def create_session(self, user: CurrentUser) -> ChatSession:
        return await self.sessions.create(user.user_id)

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        if session_id is None:
            session_id = (await self.sessions.create(user.user_id)).session_id
        else:
            await self.sessions.get_owned(user, session_id)

        # Solo se envía el mensaje: el nodo ingest copia la pregunta a "question"
        result = await self.agent.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": session_id}},
            # El contexto se arma por pregunta porque lleva al usuario del token
            context=GraphContext(vector_store=self.vector_store, user=user),
        )
        # Después del grafo: si falla, la sesión no registra una actividad que no ocurrió
        await self.sessions.record_question(session_id, question)
        return ChatAnswer(session_id=session_id, response=result.get("response", ""))

    async def list_sessions(self, user: CurrentUser) -> list[ChatSession]:
        return await self.sessions.list_for_user(user.user_id)

    async def get_history(self, user: CurrentUser, session_id: str) -> list[ChatMessage]:
        await self.sessions.get_owned(user, session_id)
        history = []
        for message in await memory.get_session_messages(self.agent, session_id):
            history.append(ChatMessage(role=message.type, content=message.text))
        return history

    async def delete_session(self, user: CurrentUser, session_id: str) -> None:
        await self.sessions.get_owned(user, session_id)
        await self.sessions.delete(session_id)
