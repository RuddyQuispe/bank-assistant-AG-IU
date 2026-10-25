from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.graphs.state.bank_state import BankState
from digital_wallet_rqm.memory.checkpointer import get_checkpointer
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatMessage
from digital_wallet_rqm.services.langgraph_chat_service import LangGraphChatService

RUDDY = CurrentUser(user_id="1", nickname="ruddy")


def _echo_node(state: BankState) -> dict:
    # Simula el agente: responde con eco de la pregunta
    response = f"eco: {state['question']}"
    return {"response": response, "messages": [AIMessage(content=response)]}


def _build_service(checkpointer) -> LangGraphChatService:
    builder = StateGraph(BankState)
    builder.add_node("echo", _echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    agent = builder.compile(checkpointer=checkpointer)
    # El grafo de prueba no usa el vector store
    return LangGraphChatService(agent, checkpointer, vector_store=None)


def test_ask_returns_response_and_keeps_session(tmp_path):
    with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)

        answer = service.ask("hola", RUDDY, session_id="s1")

        assert answer.session_id == "s1"
        assert answer.response == "eco: hola"


def test_ask_without_session_creates_a_new_one(tmp_path):
    with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)

        answer = service.ask("hola", RUDDY)

        assert answer.session_id != ""
        assert service.list_sessions() == [answer.session_id]


def test_history_has_user_and_ai_messages_in_order(tmp_path):
    with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)
        service.ask("hola", RUDDY, session_id="s1")
        service.ask("saldo", RUDDY, session_id="s1")

        history = service.get_history("s1")

        assert history == [
            ChatMessage(role="human", content="hola"),
            ChatMessage(role="ai", content="eco: hola"),
            ChatMessage(role="human", content="saldo"),
            ChatMessage(role="ai", content="eco: saldo"),
        ]


def test_delete_session_removes_it(tmp_path):
    with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        service = _build_service(checkpointer)
        service.ask("hola", RUDDY, session_id="s1")
        service.ask("hola", RUDDY, session_id="s2")

        service.delete_session("s1")

        assert service.list_sessions() == ["s2"]
        assert service.get_history("s1") == []
