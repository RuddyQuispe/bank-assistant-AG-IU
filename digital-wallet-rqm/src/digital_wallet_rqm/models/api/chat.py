from dataclasses import dataclass


@dataclass(frozen=True)
class ChatAnswer:
    session_id: str
    response: str


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
