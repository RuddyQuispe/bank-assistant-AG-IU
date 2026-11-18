from datetime import datetime

from pydantic import BaseModel, Field

from digital_wallet_rqm.domain.models import AccountBalance, ChatSession


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, examples=["¿Cuánto cuesta el mantenimiento de una tarjeta de crédito?"])
    session_id: str | None = Field(
        default=None,
        description="Id de una sesión existente; si se omite, el servidor crea una nueva y devuelve su id",
    )


class ChatResponse(BaseModel):
    session_id: str = Field(examples=["3f6c1c2e-8a1b-4c9e-9f2a-1d2e3f4a5b6c"])
    response: str = Field(examples=["Respuesta del asistente con las fuentes citadas al final."])


class BalanceCardResponse(BaseModel):
    """Tarjeta del saldo que el agente mostró en el chat"""

    account_number: str = Field(examples=["1001234567"])
    account_type: str = Field(examples=["Caja de ahorro"])
    currency: str = Field(description="Código ISO 4217", examples=["BOB"])
    available: str = Field(description="Saldo disponible como texto, sin perder decimales", examples=["1500.50"])

    @classmethod
    def from_domain(cls, card: AccountBalance) -> "BalanceCardResponse":
        return cls(
            account_number=card.account_number,
            account_type=card.account_type,
            currency=card.currency,
            available=str(card.available),
        )


class MessageResponse(BaseModel):
    role: str = Field(description="human o ai", examples=["human"])
    content: str = Field(examples=["¿Cuánto cuesta el mantenimiento de una tarjeta de crédito?"])
    card: BalanceCardResponse | None = Field(
        default=None, description="Tarjeta del saldo que mostró el agente; en ese caso content viene vacío"
    )


class SessionResponse(BaseModel):
    session_id: str = Field(examples=["3f6c1c2e-8a1b-4c9e-9f2a-1d2e3f4a5b6c"])
    title: str | None = Field(
        description="Primeros 150 caracteres de la primera pregunta; null si aún no hay preguntas"
    )
    created_at: datetime
    updated_at: datetime = Field(description="Última actividad; el listado se ordena por este campo")

    @classmethod
    def from_domain(cls, session: ChatSession) -> "SessionResponse":
        return cls(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
