from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from scalar_fastapi import Theme, get_scalar_api_reference

from digital_wallet_rqm.api.routers import agui_router, auth_router, chat_router, index_router
from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.core.embedding import get_or_create_vector_store
from digital_wallet_rqm.graphs.rag_agent import build_rag_agent
from digital_wallet_rqm.memory.checkpoint_session_repository import CheckpointSessionRepository
from digital_wallet_rqm.memory.checkpointer import get_checkpointer
from digital_wallet_rqm.services.auth_service import AuthService
from digital_wallet_rqm.services.indexing_service import DocumentIndexer
from digital_wallet_rqm.services.langgraph_chat_service import LangGraphChatService
from digital_wallet_rqm.services.session_repository import SessionForbiddenError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Lo que va antes del yield corre al arrancar la app y lo de después al apagarla.

    # Se crea primero: si falta JWT_SECRET la app no arranca
    app.state.auth_service = AuthService(settings.JWT_SECRET)

    # La conexión del checkpointer se abre una sola vez y se cierra al salir del "async with"
    async with get_checkpointer() as checkpointer:
        # Una sola instancia del vector store, compartida por el chat y el indexador
        vector_store = get_or_create_vector_store(settings.CHROMA_COLLECTION)

        document_indexer = DocumentIndexer(vector_store)
        # Indexación al arrancar desactivada por ahora: gasta tokens de embedding en cada arranque
        # con la colección vacía y, si falla, la API no levanta. Indexar con POST /admin/index.
        # Para volver a habilitarla, descomentar:
        # if document_indexer.count() == 0:
        #     document_indexer.sync()

        app.state.document_indexer = document_indexer
        # Grafo, sesiones y vector store se comparten entre el chat REST y el adaptador AG-UI
        app.state.rag_agent = build_rag_agent(checkpointer)
        app.state.session_repository = CheckpointSessionRepository(checkpointer)
        app.state.vector_store = vector_store
        app.state.chat_service = LangGraphChatService(
            agent=app.state.rag_agent,
            sessions=app.state.session_repository,
            vector_store=vector_store,
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
    app.add_exception_handler(SessionForbiddenError, _session_forbidden)
    app.include_router(auth_router.router)
    app.include_router(chat_router.router)
    app.include_router(index_router.router)
    app.include_router(agui_router.router)

    if docs_enabled:
        # Se valida al arrancar: un SCALAR_THEME mal escrito falla aquí y no al abrir la página
        theme = Theme(settings.SCALAR_THEME)

        def scalar_docs() -> HTMLResponse:
            return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title, theme=theme)

        app.add_api_route(settings.SCALAR_PATH, scalar_docs, include_in_schema=False)

    return app


async def _session_forbidden(request: Request, error: Exception) -> JSONResponse:
    # Mismo formato que el resto de errores ({"detail": ...}); no se revela de quién es la sesión
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "La sesión pertenece a otro usuario"})


app = create_app()
