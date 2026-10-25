from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from digital_wallet_rqm.config.settings import settings

MemoryBackend = Literal["sqlite", "postgres"]


@contextmanager
def get_checkpointer(
    backend: str = settings.MEMORY_BACKEND,
    sqlite_path: Path = settings.SQLITE_DB_PATH,
    database_url: str | None = settings.DATABASE_URL,
) -> Iterator[BaseCheckpointSaver]:
    """Abre el checkpointer del motor configurado y cierra la conexión al salir."""
    if backend == "sqlite":
        # SQLite no crea carpetas: se asegura que exista el directorio
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
            yield saver
    elif backend == "postgres":
        if not database_url:
            raise ValueError("DATABASE_URL es obligatorio para el motor postgres")
        with PostgresSaver.from_conn_string(database_url) as saver:
            # Crea o migra las tablas; es seguro llamarlo en cada arranque
            saver.setup()
            yield saver
    else:
        raise ValueError(f"Motor de memoria no soportado: {backend}")


def list_sessions(checkpointer: BaseCheckpointSaver) -> list[str]:
    """Devuelve los thread_id únicos (sesiones) guardados."""
    # Hay un checkpoint por paso del grafo, por eso se eliminan duplicados
    return list(dict.fromkeys(
        checkpoint.config["configurable"]["thread_id"]
        for checkpoint in checkpointer.list(None)
    ))


def get_session_messages(graph: CompiledStateGraph[Any, Any, Any, Any], session_id: str) -> list[BaseMessage]:
    """Devuelve los mensajes del último estado de la sesión."""
    state = graph.get_state({"configurable": {"thread_id": session_id}})
    return state.values.get("messages", [])


def delete_session(checkpointer: BaseCheckpointSaver, session_id: str) -> None:
    """Elimina todos los checkpoints de la sesión."""
    checkpointer.delete_thread(session_id)
