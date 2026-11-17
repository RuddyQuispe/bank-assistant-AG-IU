from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.application.auth_use_cases import AuthUseCases
from digital_wallet_rqm.application.chat_use_cases import ChatUseCases
from digital_wallet_rqm.application.usage_use_cases import UsageUseCases
from digital_wallet_rqm.domain.errors import UnauthorizedError
from digital_wallet_rqm.domain.models import CurrentUser
from digital_wallet_rqm.infrastructure.inbound.agui.wallet_agui_adapter import WalletAGUIAdapter
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.rag_agent import RagAgent
from digital_wallet_rqm.infrastructure.outbound.vectorstore.document_indexer import DocumentIndexer

# auto_error=False: si falta el header respondemos 401 nosotros, con el mismo formato que un token inválido
bearer_scheme = HTTPBearer(auto_error=False)


def get_chat_use_cases(request: Request) -> ChatUseCases:
    """Entrega el servicio creado al arrancar la app (ver lifespan en main.py)"""
    use_cases: ChatUseCases = request.app.state.chat_use_cases
    return use_cases


def get_usage_use_cases(request: Request) -> UsageUseCases:
    """Entrega la consulta de consumo creada al arrancar la app (ver lifespan en main.py)"""
    use_cases: UsageUseCases = request.app.state.usage_use_cases
    return use_cases


def get_rag_agent(request: Request) -> RagAgent:
    """Entrega el grafo compilado al arrancar la app (lo usa el adaptador AG-UI)"""
    agent: RagAgent = request.app.state.rag_agent
    return agent


def get_vector_store(request: Request) -> VectorStore:
    """Entrega el vector store compartido creado al arrancar la app"""
    vector_store: VectorStore = request.app.state.vector_store
    return vector_store


def get_document_indexer(request: Request) -> DocumentIndexer:
    """Entrega el indexador creado al arrancar la app (ver lifespan en main.py)"""
    indexer: DocumentIndexer = request.app.state.document_indexer
    return indexer


def get_auth_use_cases(request: Request) -> AuthUseCases:
    """Entrega el servicio de auth creado al arrancar la app (ver lifespan en main.py)"""
    use_cases: AuthUseCases = request.app.state.auth_use_cases
    return use_cases


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthUseCases = Depends(get_auth_use_cases),
) -> CurrentUser:
    """Filtro de auth: lee el token "Authorization: Bearer ..." y devuelve el usuario, o responde 401"""
    if credentials is None:
        raise UnauthorizedError("Falta el token")
    # Un token inválido lanza InvalidTokenError: el handler global responde 401 "Token inválido"
    return auth.current_user(credentials.credentials)


def get_wallet_adapter(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    agent: Annotated[RagAgent, Depends(get_rag_agent)],
    vector_store: Annotated[VectorStore, Depends(get_vector_store)],
) -> WalletAGUIAdapter:
    """Un adaptador AG-UI por request: lleva al usuario del token en el contexto del grafo"""
    return WalletAGUIAdapter(graph=agent, context=GraphContext(vector_store=vector_store, user=user))


# Datos de la request: los manda el cliente
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]  # header Authorization
AcceptHeader = Annotated[str, Header()]  # header Accept

# Servicios: instancias del servidor creadas al arrancar (lifespan) o armadas por request
ChatService = Annotated[ChatUseCases, Depends(get_chat_use_cases)]
WalletAgentService = Annotated[WalletAGUIAdapter, Depends(get_wallet_adapter)]
