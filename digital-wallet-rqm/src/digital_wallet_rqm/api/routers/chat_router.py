from fastapi import APIRouter, Depends, status

from digital_wallet_rqm.api.dependencies import get_chat_service, get_current_user
from digital_wallet_rqm.api.schemas.chat_schema import ChatRequest, ChatResponse, MessageResponse
from digital_wallet_rqm.api.schemas.error_schema import UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatService

# Todas las rutas del chat exigen token
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
    responses=UNAUTHORIZED_RESPONSE,
)


@router.post("", summary="Preguntar al agente")
async def ask(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Si no se envía `session_id`, se crea una sesión nueva y se devuelve su id."""
    answer = await service.ask(body.question, user, body.session_id)
    return ChatResponse(session_id=answer.session_id, response=answer.response)


@router.get("/sessions", summary="Listar sesiones")
async def list_sessions(service: ChatService = Depends(get_chat_service)) -> list[str]:
    """Devuelve los ids de las sesiones guardadas."""
    return await service.list_sessions()


@router.get("/sessions/{session_id}/history", summary="Historial de una sesión")
async def get_history(session_id: str, service: ChatService = Depends(get_chat_service)) -> list[MessageResponse]:
    """Devuelve los mensajes de la sesión en orden."""
    messages = []
    for message in await service.get_history(session_id):
        messages.append(MessageResponse(role=message.role, content=message.content))
    return messages


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una sesión")
async def delete_session(session_id: str, service: ChatService = Depends(get_chat_service)) -> None:
    """Elimina la sesión y todo su historial."""
    await service.delete_session(session_id)
