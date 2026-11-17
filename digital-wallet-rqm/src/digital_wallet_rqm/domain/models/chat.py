from dataclasses import dataclass, field

from digital_wallet_rqm.domain.models.token_usage import TokenUsage


@dataclass
class AgentReply:
    """Lo que devuelve el agente por una pregunta: la respuesta y los tokens que consumió"""

    response: str
    usage: TokenUsage = field(default_factory=TokenUsage)


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
