from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, examples=["¿Cuánto cuesta el mantenimiento de una tarjeta de crédito?"])
    session_id: str | None = Field(
        default=None, description="Id de una sesión existente; si se omite se crea una nueva"
    )


class ChatResponse(BaseModel):
    session_id: str = Field(examples=["3f6c1c2e-8a1b-4c9e-9f2a-1d2e3f4a5b6c"])
    response: str = Field(examples=["Respuesta del asistente con las fuentes citadas al final."])


class MessageResponse(BaseModel):
    role: str = Field(description="human o ai", examples=["human"])
    content: str = Field(examples=["¿Cuánto cuesta el mantenimiento de una tarjeta de crédito?"])
