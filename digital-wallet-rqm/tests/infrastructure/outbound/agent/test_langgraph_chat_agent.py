"""Adaptador ChatAgent sobre un grafo de prueba y el checkpointer SQLite real"""

from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.domain.models import AccountBalance, ChatMessage, CurrentUser, TokenUsage
from digital_wallet_rqm.infrastructure.outbound.agent.langgraph_chat_agent import LangGraphChatAgent
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState
from digital_wallet_rqm.infrastructure.outbound.persistence.checkpointer import get_checkpointer

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")


def _echo_node(state: BankState) -> dict[str, Any]:
    # Simula el grafo RAG: dos llamadas al LLM (como analyzer e interpreter), cada una con su consumo
    route = _FakeChatModel(usage={"input_tokens": 500, "output_tokens": 10, "total_tokens": 510}).invoke("rutear")
    response = f"eco: {state['messages'][-1].text}"
    usage = {"input_tokens": 312, "output_tokens": 85, "total_tokens": 397}
    answer = _FakeChatModel(usage=usage, reply=response).invoke("redactar")
    assert route is not None
    return {"response": response, "messages": [AIMessage(content=answer.text)]}


class _FakeChatModel(GenericFakeChatModel):
    """Modelo falso que informa usage_metadata como Gemini"""

    def __init__(self, usage: dict[str, int], reply: str = "ok") -> None:
        super().__init__(messages=iter([AIMessage(content=reply, usage_metadata=usage)]))  # type: ignore[arg-type]


@pytest.fixture
async def agent(tmp_path: Path) -> AsyncIterator[LangGraphChatAgent]:
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        builder = StateGraph(BankState)
        builder.add_node("echo", _echo_node)
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)
        graph: Any = builder.compile(checkpointer=checkpointer)
        # El grafo de prueba no usa el vector store
        yield LangGraphChatAgent(graph, checkpointer, vector_store=None)  # type: ignore[arg-type]


async def test_answer_returns_the_graph_response(agent: LangGraphChatAgent) -> None:
    assert (await agent.answer("hola", "s1", RUDDY)).response == "eco: hola"


async def test_answer_reports_the_tokens_of_every_llm_call_in_the_run(agent: LangGraphChatAgent) -> None:
    reply = await agent.answer("hola", "s1", RUDDY)

    assert reply.usage == TokenUsage(input_tokens=812, output_tokens=95)


async def test_each_answer_counts_only_its_own_run(agent: LangGraphChatAgent) -> None:
    await agent.answer("hola", "s1", RUDDY)

    assert (await agent.answer("otra", "s1", RUDDY)).usage == TokenUsage(812, 95)


async def test_history_keeps_both_turns_per_session(agent: LangGraphChatAgent) -> None:
    await agent.answer("hola", "s1", RUDDY)
    await agent.answer("saldo", "s1", RUDDY)
    await agent.answer("otra", "s2", RUDDY)

    assert await agent.history("s1") == [
        ChatMessage(role="human", content="hola"),
        ChatMessage(role="ai", content="eco: hola"),
        ChatMessage(role="human", content="saldo"),
        ChatMessage(role="ai", content="eco: saldo"),
    ]


async def test_history_hides_client_tool_calls_and_their_results(agent: LangGraphChatAgent) -> None:
    # Un turno de interface: tool call sin texto, resultado del navegador y la confirmación del agente
    call = AIMessage(content="", tool_calls=[{"name": "set_font", "args": {"font": "Roboto"}, "id": "c1"}])
    messages = [HumanMessage(content="cambia a Roboto"), call, ToolMessage(content="ok: Roboto", tool_call_id="c1")]
    await agent.graph.aupdate_state(
        {"configurable": {"thread_id": "s1"}}, {"messages": [*messages, AIMessage(content="Listo, usé Roboto.")]}
    )

    assert await agent.history("s1") == [
        ChatMessage(role="human", content="cambia a Roboto"),
        ChatMessage(role="ai", content="Listo, usé Roboto."),
    ]


async def test_history_returns_the_saved_balance_card(agent: LangGraphChatAgent) -> None:
    args = {"account_number": "1001234567", "account_type": "Caja de ahorro", "currency": "BOB", "available": "1500.50"}
    call = AIMessage(content="", tool_calls=[{"name": "show_account_balance", "args": args, "id": "balance-1"}])
    displayed = ToolMessage(content="displayed", tool_call_id="balance-1", name="show_account_balance")
    answer = AIMessage(content="Acá tenés el saldo de tu caja de ahorro.")
    await agent.graph.aupdate_state(
        {"configurable": {"thread_id": "s1"}},
        {"messages": [HumanMessage(content="cuánto tengo"), call, displayed, answer]},
    )

    card = AccountBalance(
        account_number="1001234567", account_type="Caja de ahorro", currency="BOB", available=Decimal("1500.50")
    )
    assert await agent.history("s1") == [
        ChatMessage(role="human", content="cuánto tengo"),
        ChatMessage(role="ai", content="", card=card),
        ChatMessage(role="ai", content="Acá tenés el saldo de tu caja de ahorro."),
    ]


async def test_history_skips_a_card_with_broken_data(agent: LangGraphChatAgent) -> None:
    call = AIMessage(content="", tool_calls=[{"name": "show_account_balance", "args": {"currency": "BOB"}, "id": "b1"}])
    await agent.graph.aupdate_state(
        {"configurable": {"thread_id": "s1"}}, {"messages": [HumanMessage(content="cuánto tengo"), call]}
    )

    assert await agent.history("s1") == [ChatMessage(role="human", content="cuánto tengo")]


async def test_forget_removes_only_that_session_history(agent: LangGraphChatAgent) -> None:
    await agent.answer("hola", "s1", RUDDY)
    await agent.answer("hola", "s2", RUDDY)

    await agent.forget("s1")

    assert await agent.history("s1") == []
    assert len(await agent.history("s2")) == 2
