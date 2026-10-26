from dataclasses import dataclass


@dataclass
class ChatAnswer:
    """Respuesta del agente a una pregunta, con la sesión donde quedó guardada"""

    session_id: str
    response: str


@dataclass
class ChatMessage:
    """Un mensaje del historial: role es "human" o "ai" """

    role: str
    content: str
