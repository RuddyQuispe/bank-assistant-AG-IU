from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from digital_wallet_rqm.core.document_builder import make_chunk_ids
from digital_wallet_rqm.services.indexing_service import DocumentIndexer


def _build_indexer(tmp_path) -> tuple[DocumentIndexer, Chroma]:
    # Embeddings falsos: no se llama a Gemini
    vector_store = Chroma(
        collection_name="test",
        embedding_function=DeterministicFakeEmbedding(size=8),
        persist_directory=str(tmp_path / "chroma"),
    )
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    return DocumentIndexer(vector_store, documents_dir), vector_store


def _indexed_files(vector_store: Chroma) -> set[str]:
    return {metadata["file_name"] for metadata in vector_store.get()["metadatas"]}


def test_make_chunk_ids_uses_file_page_and_start_index():
    chunks = [
        Document(page_content="a", metadata={"file_name": "manual.pdf", "page": 3, "start_index": 120}),
        Document(page_content="b", metadata={"file_name": "notas.txt", "start_index": 0}),
    ]

    assert make_chunk_ids(chunks) == ["manual.pdf:3:120", "notas.txt:0:0"]


def test_sync_indexes_documents_from_folder(tmp_path):
    indexer, vector_store = _build_indexer(tmp_path)
    (tmp_path / "documents" / "tarifas.txt").write_text("La comision es 1%.", encoding="utf-8")

    total = indexer.sync()

    assert total == 1
    assert _indexed_files(vector_store) == {"tarifas.txt"}


def test_sync_twice_does_not_duplicate_chunks(tmp_path):
    indexer, _ = _build_indexer(tmp_path)
    (tmp_path / "documents" / "tarifas.txt").write_text("La comision es 1%.", encoding="utf-8")

    indexer.sync()
    total = indexer.sync()

    assert total == 1


def test_sync_removes_chunks_of_deleted_files(tmp_path):
    indexer, vector_store = _build_indexer(tmp_path)
    (tmp_path / "documents" / "tarifas.txt").write_text("La comision es 1%.", encoding="utf-8")
    (tmp_path / "documents" / "limites.txt").write_text("El limite diario es 500.", encoding="utf-8")
    indexer.sync()

    (tmp_path / "documents" / "limites.txt").unlink()
    total = indexer.sync()

    assert total == 1
    assert _indexed_files(vector_store) == {"tarifas.txt"}


def test_sync_with_empty_folder_keeps_existing_index(tmp_path):
    indexer, _ = _build_indexer(tmp_path)
    (tmp_path / "documents" / "tarifas.txt").write_text("La comision es 1%.", encoding="utf-8")
    indexer.sync()

    (tmp_path / "documents" / "tarifas.txt").unlink()
    total = indexer.sync()

    assert total == 1


def test_rebuild_removes_everything_not_in_folder(tmp_path):
    indexer, vector_store = _build_indexer(tmp_path)
    (tmp_path / "documents" / "tarifas.txt").write_text("La comision es 1%.", encoding="utf-8")
    # Chunk cargado por fuera del indexador: sync no lo conoce, rebuild si lo elimina
    vector_store.add_documents([Document(page_content="viejo", metadata={"file_name": "viejo.txt"})], ids=["viejo"])

    total = indexer.rebuild()

    assert total == 1
    assert _indexed_files(vector_store) == {"tarifas.txt"}


def test_count_returns_zero_for_empty_collection(tmp_path):
    indexer, _ = _build_indexer(tmp_path)

    assert indexer.count() == 0
