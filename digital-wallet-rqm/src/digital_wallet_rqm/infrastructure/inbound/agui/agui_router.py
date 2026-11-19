from collections.abc import AsyncIterator

from ag_ui.core import RunAgentInput, RunFinishedEvent, UserMessage
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from digital_wallet_rqm.application.chat_use_cases import ChatUseCases
from digital_wallet_rqm.domain.models import CurrentUser, TokenUsage
from digital_wallet_rqm.infrastructure.inbound.agui.wallet_agui_adapter import AGENT_NAME, WalletAGUIAdapter
from digital_wallet_rqm.infrastructure.inbound.dependencies import (
    AcceptHeader,
    AuthenticatedUser,
    ChatService,
    WalletAgentService,
    get_current_user,
)
from digital_wallet_rqm.infrastructure.inbound.error_schema import (
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)

# Adaptador AG-UI: mismo grafo que /chat, pero con respuesta en streaming (SSE)
router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)],
    responses={**UNAUTHORIZED_RESPONSE, **NOT_FOUND_RESPONSE, **FORBIDDEN_RESPONSE},
)


@router.post(f"/{AGENT_NAME}", summary="Correr el agente por AG-UI (streaming)")
async def run_wallet_agent(
    # Request
    body: RunAgentInput,
    user: AuthenticatedUser,
    # Servicios
    chat: ChatService,
    agent: WalletAgentService,
    # Request (al final porque tiene valor por defecto)
    accept: AcceptHeader = "text/event-stream",
) -> StreamingResponse:
    """`threadId` es una sesión creada antes con `POST /chat/sessions` (el id lo asigna el servidor).

    Si no existe responde 404 y si es de otro usuario, 403, antes de abrir el stream.
    """
    await chat.start_run(user, body.thread_id)

    encoder = EventEncoder(accept=accept)
    events = _stream_run(agent, encoder, chat, user, body)
    return StreamingResponse(events, media_type=encoder.get_content_type())


async def _stream_run(
    adapter: WalletAGUIAdapter,
    encoder: EventEncoder,
    chat: ChatUseCases,
    user: CurrentUser,
    input_data: RunAgentInput,
) -> AsyncIterator[str]:
    """Emite los eventos AG-UI del run; si terminó bien, registra la pregunta y los tokens consumidos"""
    question = _last_user_text(input_data)
    # Los errores del grafo llegan como evento RUN_ERROR: el status 200 ya se envió
    finished: RunFinishedEvent | None = None
    async for event in adapter.run(input_data):
        if isinstance(event, RunFinishedEvent):
            finished = event
        yield encoder.encode(event)
    # Igual que en /chat: actividad y consumo solo si el run terminó bien
    if finished is not None:
        await chat.finish_run(user, input_data.thread_id, question, _run_usage(finished))


def _run_usage(finished: RunFinishedEvent) -> TokenUsage:
    """Suma los tokens que el adaptador juntó de todas las llamadas al LLM (una entrada por modelo)"""
    total = TokenUsage()
    for entry in finished.usage or []:
        total += TokenUsage(entry.input_tokens or 0, entry.output_tokens or 0)
    print(f"[usage]: in={total.input_tokens} out={total.output_tokens}")
    return total


def _last_user_text(input_data: RunAgentInput) -> str | None:
    """Texto del último mensaje del usuario (el que inicia este run); None si no es texto"""
    for message in reversed(input_data.messages):
        if isinstance(message, UserMessage):
            return message.content if isinstance(message.content, str) else None
    return None
