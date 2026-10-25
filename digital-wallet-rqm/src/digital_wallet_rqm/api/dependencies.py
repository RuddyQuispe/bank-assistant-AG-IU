from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.auth_service import AuthService, InvalidTokenError
from digital_wallet_rqm.services.chat_service import ChatService
from digital_wallet_rqm.services.indexing_service import DocumentIndexer

# auto_error=False: si falta el header respondemos 401 nosotros, con el mismo formato que un token inválido
bearer_scheme = HTTPBearer(auto_error=False)


def get_chat_service(request: Request) -> ChatService:
    """Entrega el servicio creado al arrancar la app (ver lifespan en main.py)"""
    service: ChatService = request.app.state.chat_service
    return service


def get_document_indexer(request: Request) -> DocumentIndexer:
    """Entrega el indexador creado al arrancar la app (ver lifespan en main.py)"""
    indexer: DocumentIndexer = request.app.state.document_indexer
    return indexer


def get_auth_service(request: Request) -> AuthService:
    """Entrega el servicio de auth creado al arrancar la app (ver lifespan en main.py)"""
    auth_service: AuthService = request.app.state.auth_service
    return auth_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    """Filtro de auth: lee el token "Authorization: Bearer ..." y devuelve el usuario, o responde 401"""
    if credentials is None:
        raise _unauthorized("Falta el token")
    try:
        return auth_service.read_user(credentials.credentials)
    except InvalidTokenError as error:
        raise _unauthorized("Token inválido") from error


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
