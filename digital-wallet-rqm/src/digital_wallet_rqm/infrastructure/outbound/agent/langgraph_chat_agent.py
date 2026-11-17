from langchain_core.messages import HumanMessage
from langchain_core.vectorstores import VectorStore
from langgraph.checkpoint.base import BaseCheckpointSaver

from digital_wallet_rqm.application.ports.chat_agent import ChatAgent
from digital_wallet_rqm.domain.models import AgentReply, ChatMessage, CurrentUser
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.messages import is_visible_in_chat
from digital_wallet_rqm.infrastructure.outbound.agent.rag_agent import RagAgent
from digital_wallet_rqm.infrastructure.outbound.agent.token_counter import TokenCounter
from digital_wallet_rqm.infrastructure.outbound.persistence.checkpointer import get_session_messages


class LangGraphChatAgent(ChatAgent):
    """Adaptador del puerto ChatAgent: corre el grafo RAG; el historial queda en el checkpointer"""

    def __init__(self, graph: RagAgent, checkpointer: BaseCheckpointSaver[str], vector_store: VectorStore) -> None:
        self.graph = graph
        self.checkpointer = checkpointer
        self.vector_store = vector_store

    async def answer(self, question: str, session_id: str, user: CurrentUser) -> AgentReply:
        # Un contador por run: suma los tokens de todos los nodos que llaman al LLM
        counter = TokenCounter()
        # Solo se envía el mensaje: el nodo ingest copia la pregunta a "question"
        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": session_id}, "callbacks": [counter]},
            # El contexto se arma por pregunta porque lleva al usuario del token
            context=GraphContext(vector_store=self.vector_store, user=user),
        )
        response: str = result.get("response", "")
        print(f"[usage]: user={user.user_id} in={counter.usage.input_tokens} out={counter.usage.output_tokens}")
        return AgentReply(response=response, usage=counter.usage)

    async def history(self, session_id: str) -> list[ChatMessage]:
        messages = await get_session_messages(self.graph, session_id)
        return [
            ChatMessage(role=message.type, content=message.text) for message in messages if is_visible_in_chat(message)
        ]

    async def forget(self, session_id: str) -> None:
        await self.checkpointer.adelete_thread(session_id)
