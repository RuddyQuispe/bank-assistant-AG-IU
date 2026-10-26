from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from digital_wallet_rqm.config.settings import settings

MemoryBackend = Literal["sqlite", "postgres"]


@asynccontextmanager
async def get_checkpointer(
    backend: str = settings.MEMORY_BACKEND,
    sqlite_path: Path = settings.SQLITE_DB_PATH,
    database_url: str | None = settings.DATABASE_URL,
) -> AsyncIterator[BaseCheckpointSaver[str]]:
    """Abre el checkpointer async del motor configurado y cierra la conexión al salir."""
    # Async porque el adaptador AG-UI usa aget_state/astream_events
    if backend == "sqlite":
        # SQLite no crea carpetas: se asegura que exista el directorio
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(sqlite_path)) as saver:
            yield saver
    elif backend == "postgres":
        if not database_url:
            raise ValueError("DATABASE_URL es obligatorio para el motor postgres")
        async with AsyncPostgresSaver.from_conn_string(database_url) as saver:
            # Crea o migra las tablas; es seguro llamarlo en cada arranque
            await saver.setup()
            yield saver
    else:
        raise ValueError(f"Motor de memoria no soportado: {backend}")


async def list_sessions(checkpointer: BaseCheckpointSaver[str]) -> list[str]:
    """Devuelve los thread_id únicos (sesiones) guardados."""
    # Hay un checkpoint por paso del grafo, por eso se eliminan duplicados
    thread_ids = [checkpoint.config["configurable"]["thread_id"] async for checkpoint in checkpointer.alist(None)]
    return list(dict.fromkeys(thread_ids))


async def get_session_messages(graph: CompiledStateGraph[Any, Any, Any, Any], session_id: str) -> list[BaseMessage]:
    """Devuelve los mensajes del último estado de la sesión."""
    state = await graph.aget_state({"configurable": {"thread_id": session_id}})
    messages: list[BaseMessage] = state.values.get("messages", [])
    return messages


async def delete_session(checkpointer: BaseCheckpointSaver[str], session_id: str) -> None:
    """Elimina todos los checkpoints de la sesión."""
    await checkpointer.adelete_thread(session_id)
