import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from digital_wallet_rqm.domain.errors import SessionForbiddenError, SessionNotFoundError
from digital_wallet_rqm.domain.models.current_user import CurrentUser
from digital_wallet_rqm.infrastructure.persistence.database import database_url, get_engine
from digital_wallet_rqm.infrastructure.persistence.repositories import SqlSessionRepository

pytestmark = pytest.mark.anyio

RUDDY = CurrentUser(user_id="1", nickname="ruddy")
OTHER = CurrentUser(user_id="2", nickname="otro")


@pytest.fixture
async def repository(tmp_path: Path) -> AsyncIterator[SqlSessionRepository]:
    async with get_engine(database_url(backend="sqlite", sqlite_path=tmp_path / "memory.db")) as engine:
        yield SqlSessionRepository(engine)


async def test_create_assigns_a_server_uuid_without_title(repository: SqlSessionRepository) -> None:
    session = await repository.create("1")

    assert uuid.UUID(session.session_id).version == 4
    assert session.user_id == "1"
    assert session.title is None
    assert session.created_at == session.updated_at
    assert await repository.find(session.session_id) == session


async def test_each_new_session_gets_a_different_id(repository: SqlSessionRepository) -> None:
    first = await repository.create("1")
    second = await repository.create("1")

    assert first.session_id != second.session_id


async def test_find_unknown_session_is_none(repository: SqlSessionRepository) -> None:
    assert await repository.find("no-existe") is None


async def test_first_question_sets_the_title_and_later_ones_keep_it(repository: SqlSessionRepository) -> None:
    session = await repository.create("1")

    await repository.record_question(session.session_id, "¿Cuánto cuesta\nun SPEI?")
    await repository.record_question(session.session_id, "¿Y una transferencia?")

    stored = await repository.find(session.session_id)
    assert stored is not None
    assert stored.title == "¿Cuánto cuesta un SPEI?"
    assert stored.updated_at > session.updated_at


async def test_title_keeps_at_most_150_chars(repository: SqlSessionRepository) -> None:
    session = await repository.create("1")

    await repository.record_question(session.session_id, "palabra " * 40)

    stored = await repository.find(session.session_id)
    assert stored is not None and stored.title is not None
    assert len(stored.title) <= 150


async def test_list_returns_only_own_sessions_newest_activity_first(repository: SqlSessionRepository) -> None:
    older = await repository.create("1")
    newer = await repository.create("1")
    await repository.create("2")
    await asyncio.sleep(0.01)
    # La actividad reciente sube la sesión vieja al principio
    await repository.record_question(older.session_id, "hola")

    sessions = await repository.list_for_user("1")

    assert [session.session_id for session in sessions] == [older.session_id, newer.session_id]


async def test_delete_removes_only_that_session(repository: SqlSessionRepository) -> None:
    session = await repository.create("1")
    kept = await repository.create("1")

    await repository.delete(session.session_id)

    assert await repository.find(session.session_id) is None
    assert await repository.find(kept.session_id) == kept


async def test_get_owned_returns_own_session(repository: SqlSessionRepository) -> None:
    session = await repository.create("1")

    assert await repository.get_owned(RUDDY, session.session_id) == session


async def test_get_owned_unknown_session_is_not_found(repository: SqlSessionRepository) -> None:
    with pytest.raises(SessionNotFoundError):
        await repository.get_owned(RUDDY, str(uuid.uuid4()))


async def test_get_owned_session_of_another_user_is_forbidden(repository: SqlSessionRepository) -> None:
    session = await repository.create(OTHER.user_id)

    with pytest.raises(SessionForbiddenError):
        await repository.get_owned(RUDDY, session.session_id)


def test_database_url_matches_the_checkpointer_backend(tmp_path: Path) -> None:
    assert database_url(backend="sqlite", sqlite_path=tmp_path / "m.db") == f"sqlite+aiosqlite:///{tmp_path}/m.db"
    assert database_url(backend="postgres", postgres_url="postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    with pytest.raises(ValueError, match="mongo"):
        database_url(backend="mongo")
