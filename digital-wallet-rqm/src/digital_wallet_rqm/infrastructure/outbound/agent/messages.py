from collections.abc import Sequence

from langchain_core.messages import BaseMessage


def format_recent_context(messages: Sequence[BaseMessage], limit: int = 2) -> str:
    """Formatea los últimos mensajes como 'Usuario: ...' / 'IA: ...'; vacío si hay menos de `limit`"""
    if len(messages) < limit:
        return ""
    return "\n".join(
        f"{"Usuario" if message.type == "human" else "IA"}: {message.content}"
        for message in messages[-limit:]
        if message.content
    )
