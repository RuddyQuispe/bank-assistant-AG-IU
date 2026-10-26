from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry

from digital_wallet_rqm.config.settings import settings

# Registra todas las entidades en Base.metadata antes del create_all
from digital_wallet_rqm.persistence.entities import Base


def database_url(
    backend: str = settings.MEMORY_BACKEND,
    sqlite_path: Path = settings.SQLITE_DB_PATH,
    postgres_url: str | None = settings.DATABASE_URL,
) -> str:
    """URL async de SQLAlchemy para la misma base que usa el checkpointer de LangGraph"""
    if backend == "sqlite":
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{sqlite_path}"
    if backend == "postgres":
        if not postgres_url:
            raise ValueError("DATABASE_URL es obligatorio para el motor postgres")
        # psycopg 3 sirve tanto para el checkpointer como para SQLAlchemy async
        return postgres_url.replace("postgresql://", "postgresql+psycopg://", 1)
    raise ValueError(f"Motor de memoria no soportado: {backend}")


@asynccontextmanager
async def get_engine(url: str | None = None) -> AsyncIterator[AsyncEngine]:
    """Abre el engine, crea las tablas que falten y lo cierra al salir (igual que get_checkpointer).

    create_all equivale a ddl-auto=update pero solo crea: nunca modifica columnas existentes.
    """
    engine = create_async_engine(url or database_url())
    if engine.dialect.name == "sqlite":
        event.listen(engine.sync_engine, "connect", _configure_sqlite)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Fábrica de sesiones ORM (equivalente al EntityManager); la usan los repositorios"""
    # expire_on_commit=False: las entidades se pueden leer después del commit para convertirlas a dominio
    return async_sessionmaker(engine, expire_on_commit=False)


def _configure_sqlite(connection: DBAPIConnection, record: ConnectionPoolEntry) -> None:
    # El checkpointer escribe en el mismo archivo con otra conexión: WAL permite leer mientras otro
    # escribe y busy_timeout espera el lock en vez de fallar con "database is locked"
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
