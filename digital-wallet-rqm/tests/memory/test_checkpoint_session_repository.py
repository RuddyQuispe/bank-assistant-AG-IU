from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from digital_wallet_rqm.exceptions import SessionForbiddenError
from digital_wallet_rqm.memory.checkpoint_session_repository import CheckpointSessionRepository, owner_metadata
from digital_wallet_rqm.memory.checkpointer import get_checkpointer
from digital_wallet_rqm.models.current_user import CurrentUser

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
OTHER = CurrentUser(user_id="2", nickname="otro")

Graph = CompiledStateGraph[Any, Any, Any, Any]
Setup = tuple[Graph, CheckpointSessionRepository]


def _echo_node(state: MessagesState) -> dict[str, Any]:
    return {"messages": [AIMessage(content="eco")]}


@pytest.fixture
async def setup(tmp_path: Path) -> AsyncIterator[Setup]:
    async with get_checkpointer(backend="sqlite", sqlite_path=tmp_path / "memory.db") as checkpointer:
        builder = StateGraph(MessagesState)
        builder.add_node("echo", _echo_node)
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)
        yield builder.compile(checkpointer=checkpointer), CheckpointSessionRepository(checkpointer)


async def _chat(graph: Graph, session_id: str, user: CurrentUser | None) -> None:
    config: dict[str, Any] = {"configurable": {"thread_id": session_id}}
    if user is not None:
        config["metadata"] = owner_metadata(user.user_id)
    await graph.ainvoke({"messages": [HumanMessage(content="hola")]}, config)


async def test_find_owner_returns_user_of_the_session(setup: Setup) -> None:
    graph, repository = setup
    await _chat(graph, "s1", RUDDY)

    assert await repository.find_owner("s1") == "1"


async def test_find_owner_of_new_session_is_none(setup: Setup) -> None:
    _, repository = setup

    assert await repository.find_owner("nueva") is None


async def test_list_for_user_returns_only_own_sessions(setup: Setup) -> None:
    graph, repository = setup
    await _chat(graph, "s1", RUDDY)
    await _chat(graph, "s1", RUDDY)
    await _chat(graph, "s2", OTHER)
    await _chat(graph, "s3", RUDDY)

    assert sorted(await repository.list_for_user("1")) == ["s1", "s3"]
    assert await repository.list_for_user("2") == ["s2"]


async def test_delete_removes_only_that_session(setup: Setup) -> None:
    graph, repository = setup
    await _chat(graph, "s1", RUDDY)
    await _chat(graph, "s2", RUDDY)

    await repository.delete("s1")

    assert await repository.list_for_user("1") == ["s2"]
    assert await repository.find_owner("s1") is None


async def test_ensure_owner_allows_new_and_own_sessions(setup: Setup) -> None:
    graph, repository = setup
    await _chat(graph, "s1", RUDDY)

    await repository.ensure_owner(RUDDY, "s1")
    await repository.ensure_owner(RUDDY, "nueva")


async def test_ensure_owner_rejects_session_of_another_user(setup: Setup) -> None:
    graph, repository = setup
    await _chat(graph, "s1", OTHER)

    with pytest.raises(SessionForbiddenError):
        await repository.ensure_owner(RUDDY, "s1")


async def test_ensure_owner_rejects_session_without_owner(setup: Setup) -> None:
    # Sesiones guardadas antes de registrar dueños: nadie puede usarlas
    graph, repository = setup
    await _chat(graph, "legacy", None)

    with pytest.raises(SessionForbiddenError):
        await repository.ensure_owner(RUDDY, "legacy")
