import hashlib
import time
from collections.abc import Callable
from pathlib import Path

from langchain_chroma import Chroma

from digital_wallet_rqm.infrastructure.outbound.vectorstore.document_builder import (
    load_directory_files,
    make_chunk_ids,
    split_documents,
)
from digital_wallet_rqm.infrastructure.settings import settings

CONTENT_HASH_KEY = "content_hash"


class DocumentIndexer:
    """Carga los documentos de una carpeta en la base vectorial.

    Solo embebe los chunks nuevos o modificados, en lotes, para no gastar ni pasar el límite por minuto.
    """

    def __init__(
        self,
        vector_store: Chroma,
        documents_dir: Path = settings.DOCUMENTS_DIR,
        batch_size: int = settings.EMBED_BATCH_SIZE,
        pause_seconds: float = settings.EMBED_BATCH_PAUSE_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.vector_store = vector_store
        self.documents_dir = documents_dir
        self.batch_size = batch_size
        self.pause_seconds = pause_seconds
        self.sleep = sleep

    def count(self) -> int:
        """Cantidad de chunks guardados en la colección"""
        return len(self.vector_store.get(include=[])["ids"])

    def sync(self) -> int:
        """Guarda los chunks nuevos o modificados y borra los de archivos eliminados.

        Nunca vacía la colección: si algo falla a mitad de camino, quedan los datos anteriores.
        """
        # 1. Leer la carpeta: si está vacía se conserva el índice actual en vez de borrarlo todo
        chunks = split_documents(load_directory_files(self.documents_dir))
        if not chunks:
            print(f"No hay documentos en {self.documents_dir}, se mantiene el índice actual")
            return self.count()
        chunk_ids = make_chunk_ids(chunks)
        for chunk in chunks:
            chunk.metadata[CONTENT_HASH_KEY] = hashlib.sha256(chunk.page_content.encode()).hexdigest()

        # 2. Comparar con lo guardado: el id dice dónde está el chunk y el hash si cambió su texto
        stored = self.vector_store.get(include=["metadatas"])
        stored_hashes = {}
        for chunk_id, metadata in zip(stored["ids"], stored["metadatas"]):
            stored_hashes[chunk_id] = (metadata or {}).get(CONTENT_HASH_KEY)
        pending = []
        for chunk_id, chunk in zip(chunk_ids, chunks):
            if stored_hashes.get(chunk_id) != chunk.metadata[CONTENT_HASH_KEY]:
                pending.append((chunk_id, chunk))

        # 3. Embeber solo lo pendiente, en lotes con pausa entre ellos por el límite por minuto
        for start in range(0, len(pending), self.batch_size):
            if start > 0:
                self.sleep(self.pause_seconds)
            batch = pending[start:start + self.batch_size]
            self.vector_store.add_documents([chunk for _, chunk in batch], ids=[chunk_id for chunk_id, _ in batch])
            print(f"Embebidos {start + len(batch)}/{len(pending)} chunks")

        # 4. Borrar lo guardado que ya no viene de la carpeta (archivo eliminado o con otros cortes)
        current_ids = set(chunk_ids)
        removed_ids = [chunk_id for chunk_id in stored_hashes if chunk_id not in current_ids]
        if removed_ids:
            self.vector_store.delete(ids=removed_ids)

        print(f"{len(chunks)} chunks: {len(pending)} embebidos, {len(removed_ids)} eliminados")
        return self.count()

    def rebuild(self) -> int:
        """Vacía la colección y vuelve a indexar todo.

        Usar solo si cambia CHUNK_SIZE o el modelo de embeddings: mientras corre, la colección queda vacía.
        """
        self.vector_store.reset_collection()
        return self.sync()
