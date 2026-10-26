from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.exceptions import UnauthorizedError
from digital_wallet_rqm.graphs.rag_agent import RagAgent
from digital_wallet_rqm.models.current_user import CurrentUser
from digital_wallet_rqm.services.auth_service import AuthService
from digital_wallet_rqm.services.chat_service import ChatService
from digital_wallet_rqm.services.indexing_service import DocumentIndexer
from digital_wallet_rqm.services.session_repository import SessionRepository

# auto_error=False: si falta el header respondemos 401 nosotros, con el mismo formato que un token inválido
bearer_scheme = HTTPBearer(auto_error=False)


def get_chat_service(request: Request) -> ChatService:
    """Entrega el servicio creado al arrancar la app (ver lifespan en main.py)"""
    service: ChatService = request.app.state.chat_service
    return service


def get_rag_agent(request: Request) -> RagAgent:
    """Entrega el grafo compilado al arrancar la app (lo usa el adaptador AG-UI)"""
    agent: RagAgent = request.app.state.rag_agent
    return agent


def get_session_repository(request: Request) -> SessionRepository:
    """Entrega el repositorio de sesiones creado al arrancar la app"""
    sessions: SessionRepository = request.app.state.session_repository
    return sessions


def get_vector_store(request: Request) -> VectorStore:
    """Entrega el vector store compartido creado al arrancar la app"""
    vector_store: VectorStore = request.app.state.vector_store
    return vector_store


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
        raise UnauthorizedError("Falta el token")
    # Un token inválido lanza InvalidTokenError: el handler global responde 401 "Token inválido"
    return auth_service.read_user(credentials.credentials)
