from fastapi import APIRouter, Depends

from digital_wallet_rqm.api.dependencies import get_current_user, get_document_indexer
from digital_wallet_rqm.api.schemas.error_schema import UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.api.schemas.index_schema import IndexResponse
from digital_wallet_rqm.services.indexing_service import DocumentIndexer

# Indexar gasta embeddings: exige token
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_user)],
    responses=UNAUTHORIZED_RESPONSE,
)


@router.post("/index", summary="Indexar documentos")
def index_documents(rebuild: bool = False, indexer: DocumentIndexer = Depends(get_document_indexer)) -> IndexResponse:
    """Carga la carpeta de documentos en la base vectorial. **Gasta tokens de embedding.**

    Por defecto guarda o actualiza los chunks; con `rebuild=true` vacía la colección antes de cargar.
    """
    if rebuild:
        total = indexer.rebuild()
    else:
        total = indexer.sync()
    return IndexResponse(chunks=total)
