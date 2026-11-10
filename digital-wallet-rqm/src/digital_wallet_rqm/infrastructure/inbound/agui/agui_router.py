from collections.abc import AsyncIterator

from ag_ui.core import EventType, RunAgentInput, UserMessage
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.application.chat_use_cases import ChatUseCases
from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.inbound.agui.wallet_agui_adapter import AGENT_NAME, WalletAGUIAdapter
from digital_wallet_rqm.infrastructure.inbound.dependencies import (
    get_chat_use_cases,
    get_current_user,
    get_rag_agent,
    get_vector_store,
)
from digital_wallet_rqm.infrastructure.inbound.error_schema import (
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.rag_agent import RagAgent

# Adaptador AG-UI: mismo grafo que /chat, pero con respuesta en streaming (SSE)
router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)],
    responses={**UNAUTHORIZED_RESPONSE, **NOT_FOUND_RESPONSE, **FORBIDDEN_RESPONSE},
)


@router.post(f"/{AGENT_NAME}", summary="Correr el agente por AG-UI (streaming)")
async def run_wallet_agent(
    input_data: RunAgentInput,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    agent: RagAgent = Depends(get_rag_agent),
    chat: ChatUseCases = Depends(get_chat_use_cases),
    vector_store: VectorStore = Depends(get_vector_store),
) -> StreamingResponse:
    """`threadId` es una sesión creada antes con `POST /chat/sessions` (el id lo asigna el servidor).

    Si no existe responde 404 y si es de otro usuario, 403, antes de abrir el stream.
    """
    await chat.start_run(user, input_data.thread_id)

    adapter = WalletAGUIAdapter(graph=agent, context=GraphContext(vector_store=vector_store, user=user))
    encoder = EventEncoder(accept=request.headers.get("accept", "text/event-stream"))
    events = _stream_run(adapter, encoder, chat, input_data)
    return StreamingResponse(events, media_type=encoder.get_content_type())


async def _stream_run(
    adapter: WalletAGUIAdapter,
    encoder: EventEncoder,
    chat: ChatUseCases,
    input_data: RunAgentInput,
) -> AsyncIterator[str]:
    """Emite los eventos AG-UI del run; si terminó bien, registra la pregunta en la sesión"""
    question = _last_user_text(input_data)
    # Los errores del grafo llegan como evento RUN_ERROR: el status 200 ya se envió
    finished = False
    async for event in adapter.run(input_data):
        finished = finished or event.type == EventType.RUN_FINISHED
        yield encoder.encode(event)
    # Igual que en /chat: título y actividad solo si el run terminó bien
    if finished and question:
        await chat.finish_run(input_data.thread_id, question)


def _last_user_text(input_data: RunAgentInput) -> str | None:
    """Texto del último mensaje del usuario (el que inicia este run); None si no es texto"""
    for message in reversed(input_data.messages):
        if isinstance(message, UserMessage):
            return message.content if isinstance(message.content, str) else None
    return None
