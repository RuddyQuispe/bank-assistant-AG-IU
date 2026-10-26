from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import VectorStore
from langgraph.checkpoint.base import BaseCheckpointSaver

from digital_wallet_rqm.application.ports.outbound.chat_agent import ChatAgent
from digital_wallet_rqm.domain.models import ChatMessage, CurrentUser
from digital_wallet_rqm.infrastructure.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.agent.rag_agent import RagAgent
from digital_wallet_rqm.infrastructure.persistence.checkpointer import get_session_messages


class LangGraphChatAgent(ChatAgent):
    """Adaptador del puerto ChatAgent: corre el grafo RAG; el historial queda en el checkpointer"""

    def __init__(self, graph: RagAgent, checkpointer: BaseCheckpointSaver[str], vector_store: VectorStore) -> None:
        self.graph = graph
        self.checkpointer = checkpointer
        self.vector_store = vector_store

    async def answer(self, question: str, session_id: str, user: CurrentUser) -> str:
        # Solo se envía el mensaje: el nodo ingest copia la pregunta a "question"
        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": session_id}},
            # El contexto se arma por pregunta porque lleva al usuario del token
            context=GraphContext(vector_store=self.vector_store, user=user),
        )
        response: str = result.get("response", "")
        return response

    async def history(self, session_id: str) -> list[ChatMessage]:
        messages = await get_session_messages(self.graph, session_id)
        return [ChatMessage(role=message.type, content=message.text) for message in messages]

    async def forget(self, session_id: str) -> None:
        await self.checkpointer.adelete_thread(session_id)
