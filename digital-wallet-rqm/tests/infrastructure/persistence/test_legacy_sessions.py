"""Sesiones guardadas antes de la tabla "sessions": el dueño estaba en la metadata del checkpoint"""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from digital_wallet_rqm.infrastructure.persistence.checkpointer import get_checkpointer
from digital_wallet_rqm.infrastructure.persistence.database import database_url, get_engine
from digital_wallet_rqm.infrastructure.persistence.entities import SessionRecord
from digital_wallet_rqm.infrastructure.persistence.legacy_sessions import import_legacy_sessions
from digital_wallet_rqm.infrastructure.persistence.repositories import SqlSessionRepository

pytestmark = pytest.mark.anyio

Graph = CompiledStateGraph[Any, Any, Any, Any]
Env = tuple[BaseCheckpointSaver[str], AsyncEngine, Graph]


@pytest.fixture
async def env(tmp_path: Path) -> AsyncIterator[Env]:
    db_path = tmp_path / "memory.db"
    async with (
        get_checkpointer(backend="sqlite", sqlite_path=db_path) as checkpointer,
        get_engine(database_url(backend="sqlite", sqlite_path=db_path)) as engine,
    ):
        builder = StateGraph(MessagesState)
        builder.add_node("echo", lambda state: {"messages": [AIMessage(content="eco")]})
        builder.add_edge(START, "echo")
        builder.add_edge("echo", END)
        yield checkpointer, engine, builder.compile(checkpointer=checkpointer)


async def _legacy_chat(graph: Graph, thread_id: str, question: str, owner: str | None) -> None:
    # Así guardaba las sesiones la versión anterior: dueño en config["metadata"]["user_id"]
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if owner is not None:
        config["metadata"] = {"user_id": owner}
    await graph.ainvoke({"messages": [HumanMessage(content=question)]}, config)


async def test_legacy_session_gets_a_row_with_owner_title_and_dates(env: Env) -> None:
    checkpointer, engine, graph = env
    await _legacy_chat(graph, "legacy-1", "¿Cuánto\ncuesta un SPEI?", "1")
    await _legacy_chat(graph, "legacy-1", "gracias", "1")

    imported = await import_legacy_sessions(engine, checkpointer)

    assert imported == 1
    session = await SqlSessionRepository(engine).find("legacy-1")
    assert session is not None
    assert session.user_id == "1"
    # El título sale de la primera pregunta, no de la última
    assert session.title == "¿Cuánto cuesta un SPEI?"
    assert session.created_at < session.updated_at


async def test_import_is_idempotent_and_keeps_existing_rows(env: Env) -> None:
    checkpointer, engine, graph = env
    repository = SqlSessionRepository(engine)
    current = await repository.create("1")
    await _legacy_chat(graph, "legacy-1", "hola", "1")

    assert await import_legacy_sessions(engine, checkpointer) == 1
    assert await import_legacy_sessions(engine, checkpointer) == 0
    assert await repository.find(current.session_id) == current


async def test_threads_without_owner_are_not_imported(env: Env) -> None:
    # Antes de registrar dueños nadie podía usarlas: siguen sin dueño y sin fila
    checkpointer, engine, graph = env
    await _legacy_chat(graph, "sin-dueno", "hola", None)

    assert await import_legacy_sessions(engine, checkpointer) == 0
    assert await SqlSessionRepository(engine).find("sin-dueno") is None


async def test_imported_session_is_listed_for_its_owner_only(env: Env) -> None:
    checkpointer, engine, graph = env
    await _legacy_chat(graph, "de-ruddy", "hola", "1")
    await _legacy_chat(graph, "de-otro", "hola", "2")

    await import_legacy_sessions(engine, checkpointer)

    repository = SqlSessionRepository(engine)
    assert [session.session_id for session in await repository.list_for_user("1")] == ["de-ruddy"]
    assert [session.session_id for session in await repository.list_for_user("2")] == ["de-otro"]


async def test_ids_of_any_length_are_imported(env: Env) -> None:
    # Antes el cliente elegía el id sin límite: las columnas no pueden tener largo fijo (Postgres lo exige)
    checkpointer, engine, graph = env
    long_id = "copilotkit-thread-" + "x" * 80
    await _legacy_chat(graph, long_id, "hola", "1")

    assert await import_legacy_sessions(engine, checkpointer) == 1
    assert await SqlSessionRepository(engine).find(long_id) is not None
    assert SessionRecord.__table__.c.session_id.type.length is None
    assert SessionRecord.__table__.c.user_id.type.length is None


async def test_database_error_is_logged_and_does_not_stop_startup(
    env: Env, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    checkpointer, engine, graph = env
    await _legacy_chat(graph, "legacy-1", "hola", "1")

    def _fail(self: AsyncSession, instances: object) -> None:
        raise SQLAlchemyError("value too long for type character varying(36)")

    monkeypatch.setattr(AsyncSession, "add_all", _fail)

    assert await import_legacy_sessions(engine, checkpointer) == 0
    assert "legacy" in caplog.text.lower()
