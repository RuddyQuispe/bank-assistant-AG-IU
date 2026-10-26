from uuid import uuid4

from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.rag_agent import RagAgent
from digital_wallet_rqm.memory import checkpointer as memory
from digital_wallet_rqm.memory.checkpoint_session_repository import owner_metadata
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatAnswer, ChatMessage, ChatService
from digital_wallet_rqm.services.session_repository import SessionRepository


class LangGraphChatService(ChatService):
    """Implementación del chat usando el agente RAG de LangGraph"""

    def __init__(self, agent: RagAgent, sessions: SessionRepository, vector_store: VectorStore) -> None:
        self.agent = agent
        self.sessions = sessions
        self.vector_store = vector_store

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        if session_id is None:
            session_id = str(uuid4())
        await self.sessions.ensure_owner(user, session_id)

        # Solo se envía el mensaje: el nodo ingest copia la pregunta a "question"
        result = await self.agent.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            # La metadata guarda al dueño en cada checkpoint de la sesión
            config={"configurable": {"thread_id": session_id}, "metadata": owner_metadata(user.user_id)},
            # El contexto se arma por pregunta porque lleva al usuario del token
            context=GraphContext(vector_store=self.vector_store, user=user),
        )
        return ChatAnswer(session_id=session_id, response=result.get("response", ""))

    async def list_sessions(self, user: CurrentUser) -> list[str]:
        return await self.sessions.list_for_user(user.user_id)

    async def get_history(self, user: CurrentUser, session_id: str) -> list[ChatMessage]:
        await self.sessions.ensure_owner(user, session_id)
        history = []
        for message in await memory.get_session_messages(self.agent, session_id):
            history.append(ChatMessage(role=message.type, content=message.text))
        return history

    async def delete_session(self, user: CurrentUser, session_id: str) -> None:
        await self.sessions.ensure_owner(user, session_id)
        await self.sessions.delete(session_id)
