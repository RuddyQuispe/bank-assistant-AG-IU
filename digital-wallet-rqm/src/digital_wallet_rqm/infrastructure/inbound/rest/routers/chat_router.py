from fastapi import APIRouter, Depends, status

from digital_wallet_rqm.application.chat_use_cases import ChatUseCases
from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.inbound.dependencies import get_chat_use_cases, get_current_user
from digital_wallet_rqm.infrastructure.inbound.error_schema import (
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from digital_wallet_rqm.infrastructure.inbound.rest.schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    MessageResponse,
    SessionResponse,
)

# Todas las rutas del chat exigen token; los errores los responde el handler global (exception_handlers.py)
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
    chat: ChatUseCases = Depends(get_chat_use_cases),
) -> ChatResponse:
    """Si no se envía `session_id`, el servidor crea una sesión nueva y devuelve su id."""
    answer = await chat.ask(body.question, user, body.session_id)
    return ChatResponse(session_id=answer.session_id, response=answer.response)


@router.post("/sessions", status_code=status.HTTP_201_CREATED, summary="Crear una sesión")
async def create_session(
    user: CurrentUser = Depends(get_current_user),
    chat: ChatUseCases = Depends(get_chat_use_cases),
) -> SessionResponse:
    """Crea una sesión vacía con id asignado por el servidor (lo usa el frontend AG-UI como `threadId`)."""
    return SessionResponse.from_domain(await chat.create_session(user))


@router.get("/sessions", summary="Listar sesiones")
async def list_sessions(
    user: CurrentUser = Depends(get_current_user),
    chat: ChatUseCases = Depends(get_chat_use_cases),
) -> list[SessionResponse]:
    """Devuelve las sesiones del usuario del token, la de actividad más reciente primero."""
    return [SessionResponse.from_domain(session) for session in await chat.list_sessions(user)]


@router.get("/sessions/{session_id}/history", summary="Historial de una sesión", responses=SESSION_ERRORS)
async def get_history(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    chat: ChatUseCases = Depends(get_chat_use_cases),
) -> list[MessageResponse]:
    """Devuelve los mensajes de la sesión en orden."""
    messages = []
    for message in await chat.get_history(user, session_id):
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
    chat: ChatUseCases = Depends(get_chat_use_cases),
) -> None:
    """Elimina la sesión y todo su historial."""
    await chat.delete_session(user, session_id)
