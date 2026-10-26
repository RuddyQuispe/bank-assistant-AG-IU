from fastapi import APIRouter, Depends, status

from digital_wallet_rqm.api.dependencies import get_chat_service, get_current_user
from digital_wallet_rqm.api.schemas.chat_schema import ChatRequest, ChatResponse, MessageResponse, SessionResponse
from digital_wallet_rqm.api.schemas.error_schema import FORBIDDEN_RESPONSE, NOT_FOUND_RESPONSE, UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.chat_service import ChatService

# Todas las rutas del chat exigen token; los errores los responde el handler global (api/exceptions)
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)],
    responses=UNAUTHORIZED_RESPONSE,
)

# Rutas que reciben un id de sesión: puede no existir (404) o ser de otro usuario (403)
SESSION_ERRORS = {**NOT_FOUND_RESPONSE, **FORBIDDEN_RESPONSE}


@router.post("", summary="Preguntar al agente", responses=SESSION_ERRORS)
async def ask(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Si no se envía `session_id`, el servidor crea una sesión nueva y devuelve su id."""
    answer = await service.ask(body.question, user, body.session_id)
    return ChatResponse(session_id=answer.session_id, response=answer.response)


@router.post("/sessions", status_code=status.HTTP_201_CREATED, summary="Crear una sesión")
async def create_session(
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> SessionResponse:
    """Crea una sesión vacía con id asignado por el servidor (lo usa el frontend AG-UI como `threadId`)."""
    return SessionResponse.from_domain(await service.create_session(user))


@router.get("/sessions", summary="Listar sesiones")
async def list_sessions(
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[SessionResponse]:
    """Devuelve las sesiones del usuario del token, la de actividad más reciente primero."""
    return [SessionResponse.from_domain(session) for session in await service.list_sessions(user)]


@router.get("/sessions/{session_id}/history", summary="Historial de una sesión", responses=SESSION_ERRORS)
async def get_history(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageResponse]:
    """Devuelve los mensajes de la sesión en orden."""
    messages = []
    for message in await service.get_history(user, session_id):
        messages.append(MessageResponse(role=message.role, content=message.content))
    return messages


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una sesión",
    responses=SESSION_ERRORS,
)
async def delete_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> None:
    """Elimina la sesión y todo su historial."""
    await service.delete_session(user, session_id)
