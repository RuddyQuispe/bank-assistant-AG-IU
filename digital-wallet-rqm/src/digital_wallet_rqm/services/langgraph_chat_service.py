from uuid import uuid4

from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import VectorStore
from langgraph.checkpoint.base import BaseCheckpointSaver

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.rag_agent import RagAgent
from digital_wallet_rqm.memory import checkpointer as memory
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatAnswer, ChatMessage, ChatService


class LangGraphChatService(ChatService):
    """Implementación del chat usando el agente RAG de LangGraph"""

    def __init__(self, agent: RagAgent, checkpointer: BaseCheckpointSaver[str], vector_store: VectorStore) -> None:
        self.agent = agent
        self.checkpointer = checkpointer
        self.vector_store = vector_store

    async def ask(self, question: str, user: CurrentUser, session_id: str | None = None) -> ChatAnswer:
        if session_id is None:
            session_id = str(uuid4())

        # Solo se envía el mensaje: el nodo ingest copia la pregunta a "question"
        result = await self.agent.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": session_id}},
            # El contexto se arma por pregunta porque lleva al usuario del token
            context=GraphContext(vector_store=self.vector_store, user=user),
        )
        return ChatAnswer(session_id=session_id, response=result.get("response", ""))

    async def list_sessions(self) -> list[str]:
        return await memory.list_sessions(self.checkpointer)

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        history = []
        for message in await memory.get_session_messages(self.agent, session_id):
            history.append(ChatMessage(role=message.type, content=message.text))
        return history

    async def delete_session(self, session_id: str) -> None:
        await memory.delete_session(self.checkpointer, session_id)
