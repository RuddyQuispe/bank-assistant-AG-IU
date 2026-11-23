from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from digital_wallet_rqm.infrastructure.outbound.vectorstore.document_builder import make_chunk_ids
from digital_wallet_rqm.infrastructure.outbound.vectorstore.document_indexer import DocumentIndexer


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


class _CountingEmbedding(DeterministicFakeEmbedding):
    """Embeddings falsos que cuentan cuantos textos se mandaron a embeber"""

    embedded_texts: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts.extend(texts)
        return super().embed_documents(texts)


def _build_counting_indexer(tmp_path, batch_size: int = 90) -> tuple[DocumentIndexer, Chroma, _CountingEmbedding, list]:
    embedding = _CountingEmbedding(size=8, embedded_texts=[])
    vector_store = Chroma(
        collection_name="test",
        embedding_function=embedding,
        persist_directory=str(tmp_path / "chroma"),
    )
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    pauses = []
    indexer = DocumentIndexer(vector_store, documents_dir, batch_size=batch_size, pause_seconds=60, sleep=pauses.append)
    return indexer, vector_store, embedding, pauses


def test_second_sync_embeds_nothing_when_documents_did_not_change(tmp_path):
    indexer, _, embedding, _ = _build_counting_indexer(tmp_path)
    (tmp_path / "documents" / "tarifas.txt").write_text("La comision es 1%.", encoding="utf-8")
    indexer.sync()
    embedding.embedded_texts.clear()

    total = indexer.sync()

    assert total == 1
    assert embedding.embedded_texts == []


def test_sync_embeds_again_a_chunk_whose_content_changed(tmp_path):
    indexer, vector_store, embedding, _ = _build_counting_indexer(tmp_path)
    file_path = tmp_path / "documents" / "tarifas.txt"
    file_path.write_text("La comision es 1%.", encoding="utf-8")
    indexer.sync()
    embedding.embedded_texts.clear()

    # Mismo archivo, pagina e inicio (mismo id), distinto texto
    file_path.write_text("La comision es 2%.", encoding="utf-8")
    total = indexer.sync()

    assert total == 1
    assert embedding.embedded_texts == ["La comision es 2%."]
    assert vector_store.get()["documents"] == ["La comision es 2%."]


def test_sync_embeds_in_batches_and_pauses_between_them(tmp_path):
    indexer, _, embedding, pauses = _build_counting_indexer(tmp_path, batch_size=2)
    for number in range(5):
        (tmp_path / "documents" / f"doc{number}.txt").write_text(f"Texto {number}.", encoding="utf-8")

    total = indexer.sync()

    assert total == 5
    assert len(embedding.embedded_texts) == 5
    # 3 lotes (2 + 2 + 1): pausa entre lotes, no despues del ultimo
    assert pauses == [60, 60]
