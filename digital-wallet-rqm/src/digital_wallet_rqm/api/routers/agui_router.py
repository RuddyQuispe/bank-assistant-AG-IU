from collections.abc import AsyncIterator

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.api.agui.wallet_agui_adapter import AGENT_NAME, WalletAGUIAdapter
from digital_wallet_rqm.api.dependencies import (
    get_current_user,
    get_rag_agent,
    get_session_repository,
    get_vector_store,
)
from digital_wallet_rqm.api.schemas.error_schema import FORBIDDEN_RESPONSE, UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.rag_agent import RagAgent
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.session_repository import SessionRepository

# Adaptador AG-UI (protocolo de CopilotKit): mismo grafo que /chat, pero con respuesta en streaming (SSE)
router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)],
    responses={**UNAUTHORIZED_RESPONSE, **FORBIDDEN_RESPONSE},
)


@router.post(f"/{AGENT_NAME}", summary="Correr el agente por AG-UI (streaming)")
async def run_wallet_agent(
    input_data: RunAgentInput,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    agent: RagAgent = Depends(get_rag_agent),
    sessions: SessionRepository = Depends(get_session_repository),
    vector_store: VectorStore = Depends(get_vector_store),
) -> StreamingResponse:
    """`threadId` es la sesión: si es de otro usuario responde 403 antes de abrir el stream."""
    await sessions.ensure_owner(user, input_data.thread_id)

    adapter = WalletAGUIAdapter(
        graph=agent,
        context=GraphContext(vector_store=vector_store, user=user),
        owner_id=user.user_id,
    )
    encoder = EventEncoder(accept=request.headers.get("accept", "text/event-stream"))

    async def events() -> AsyncIterator[str]:
        # Los errores del grafo llegan como evento RUN_ERROR: el status 200 ya se envió
        async for event in adapter.events(input_data):
            yield encoder.encode(event)

    return StreamingResponse(events(), media_type=encoder.get_content_type())
