from dataclasses import dataclass
from datetime import datetime

TITLE_MAX_LENGTH = 150


@dataclass(frozen=True)
class ChatSession:
    """Sesión de chat; los mensajes no viven aquí sino en el checkpointer de LangGraph (thread_id = session_id)"""

    session_id: str
    user_id: str
    # None hasta que llega la primera pregunta
    title: str | None
    created_at: datetime
    updated_at: datetime


def build_title(question: str, max_length: int = TITLE_MAX_LENGTH) -> str:
    """Título de la sesión: la primera pregunta en una línea, cortada en la última palabra completa"""
    text = " ".join(question.split())
    if len(text) <= max_length:
        return text
    cut = text[:max_length]
    last_space = cut.rfind(" ")
    # Sin espacios (una sola palabra larga): se corta en el límite
    return cut[:last_space] if last_space > 0 else cut
