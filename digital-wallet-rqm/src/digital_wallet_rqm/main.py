from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from scalar_fastapi import Theme, get_scalar_api_reference

from digital_wallet_rqm.application.auth_use_cases import AuthUseCases
from digital_wallet_rqm.application.chat_use_cases import ChatUseCases
from digital_wallet_rqm.infrastructure.inbound.agui import agui_router
from digital_wallet_rqm.infrastructure.inbound.error_schema import VALIDATION_ERROR_RESPONSE
from digital_wallet_rqm.infrastructure.inbound.exception_handlers import register_exception_handlers
from digital_wallet_rqm.infrastructure.inbound.rest.routers import auth_router, chat_router, index_router
from digital_wallet_rqm.infrastructure.outbound.agent.langgraph_chat_agent import LangGraphChatAgent
from digital_wallet_rqm.infrastructure.outbound.agent.rag_agent import build_rag_agent
from digital_wallet_rqm.infrastructure.outbound.persistence.checkpointer import get_checkpointer
from digital_wallet_rqm.infrastructure.outbound.persistence.database import get_engine
from digital_wallet_rqm.infrastructure.outbound.persistence.legacy_sessions import import_legacy_sessions
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import DemoUserRepository, SqlSessionRepository
from digital_wallet_rqm.infrastructure.outbound.security.jwt_token_service import JwtTokenService
from digital_wallet_rqm.infrastructure.outbound.vectorstore.document_indexer import DocumentIndexer
from digital_wallet_rqm.infrastructure.outbound.vectorstore.vector_store import get_or_create_vector_store
from digital_wallet_rqm.infrastructure.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Lo que va antes del yield corre al arrancar la app y lo de después al apagarla.
    # Aquí se arman los adaptadores y se inyectan en los casos de uso (composition root).

    # Se crea primero: si falta JWT_SECRET la app no arranca
    app.state.auth_use_cases = AuthUseCases(tokens=JwtTokenService(settings.JWT_SECRET), users=DemoUserRepository())

    # Las conexiones se abren una sola vez y se cierran al salir del "async with":
    # el checkpointer (tablas de LangGraph) y el engine de la tabla propia "sessions", en la misma base
    async with get_checkpointer() as checkpointer, get_engine() as engine:
        # Sesiones guardadas antes de la tabla "sessions" (dueño en la metadata del checkpoint): se les crea
        # la fila para que sigan accesibles. Idempotente: en los siguientes arranques no hace nada
        await import_legacy_sessions(engine, checkpointer)
        # Una sola instancia del vector store, compartida por el chat y el indexador
        vector_store = get_or_create_vector_store(settings.CHROMA_COLLECTION)

        document_indexer = DocumentIndexer(vector_store)
        # Indexación al arrancar desactivada por ahora: gasta tokens de embedding en cada arranque
        # con la colección vacía y, si falla, la API no levanta. Indexar con POST /admin/index.
        # Para volver a habilitarla, descomentar:
        # if document_indexer.count() == 0:
        #     document_indexer.sync()

        app.state.document_indexer = document_indexer
        # Grafo y vector store se comparten entre el chat REST y el adaptador AG-UI
        app.state.rag_agent = build_rag_agent(checkpointer)
        app.state.vector_store = vector_store
        # Caso de uso del chat (REST y AG-UI): recibe los adaptadores a través de sus puertos
        app.state.chat_use_cases = ChatUseCases(
            agent=LangGraphChatAgent(app.state.rag_agent, checkpointer, vector_store),
            sessions=SqlSessionRepository(engine),
        )
        yield


def create_app() -> FastAPI:
    """Arma la app; títulos y documentación se configuran desde settings (.env)"""
    docs_enabled = settings.DOCS_ENABLED
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        description=settings.API_DESCRIPTION,
        lifespan=lifespan,
        # Todas las rutas documentan el 422 con el cuerpo {error, detail} del handler global
        responses=VALIDATION_ERROR_RESPONSE,
        # None apaga la ruta: con DOCS_ENABLED=false no se expone ninguna documentación
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    # El frontend (otro origen) manda el JWT en Authorization: el navegador exige CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Manejo global de errores (equivalente a @RestControllerAdvice): ver infrastructure/inbound/exception_handlers.py
    register_exception_handlers(app)
    app.include_router(auth_router.router)
    app.include_router(chat_router.router)
    app.include_router(index_router.router)
    app.include_router(agui_router.router)

    if docs_enabled:
        # Se valida al arrancar: un SCALAR_THEME mal escrito falla aquí y no al abrir la página
        app.state.scalar_theme = Theme(settings.SCALAR_THEME)
        app.add_api_route(settings.SCALAR_PATH, _scalar_docs, include_in_schema=False)

    return app


def _scalar_docs(request: Request) -> HTMLResponse:
    """Página de Scalar con el OpenAPI de la app"""
    app = request.app
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title, theme=app.state.scalar_theme)


app = create_app()
