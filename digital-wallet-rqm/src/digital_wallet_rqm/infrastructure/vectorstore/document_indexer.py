from pathlib import Path

from langchain_chroma import Chroma

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.infrastructure.vectorstore.document_builder import (
    load_directory_files,
    make_chunk_ids,
    split_documents,
)


class DocumentIndexer:
    """Carga los documentos de una carpeta en la base vectorial"""

    def __init__(self, vector_store: Chroma, documents_dir: Path = settings.DOCUMENTS_DIR) -> None:
        self.vector_store = vector_store
        self.documents_dir = documents_dir

    def count(self) -> int:
        """Cantidad de chunks guardados en la colección"""
        return len(self.vector_store.get(include=[])["ids"])

    def sync(self) -> int:
        """Guarda o actualiza los chunks de la carpeta y borra los de archivos eliminados.

        Nunca vacía la colección: si algo falla a mitad de camino, quedan los datos anteriores.
        """
        docs = load_directory_files(self.documents_dir)
        chunks = split_documents(docs)
        if not chunks:
            # Carpeta vacía: se conserva el índice actual en vez de borrarlo todo
            print(f"No hay documentos en {self.documents_dir}, se mantiene el índice actual")
            return self.count()

        new_ids = make_chunk_ids(chunks)
        # Con ids fijos, Chroma crea los chunks nuevos y pisa los que ya existen
        self.vector_store.add_documents(chunks, ids=new_ids)

        # Lo que está guardado pero ya no viene de la carpeta es de un archivo eliminado o modificado
        current_ids = set(new_ids)
        old_ids = self.vector_store.get(include=[])["ids"]
        removed_ids = []
        for chunk_id in old_ids:
            if chunk_id not in current_ids:
                removed_ids.append(chunk_id)
        if removed_ids:
            self.vector_store.delete(ids=removed_ids)

        print(f"Indexados {len(chunks)} chunks, eliminados {len(removed_ids)}")
        return self.count()

    def rebuild(self) -> int:
        """Vacía la colección y vuelve a indexar todo.

        Usar solo si cambia CHUNK_SIZE o el modelo de embeddings: mientras corre, la colección queda vacía.
        """
        self.vector_store.reset_collection()
        return self.sync()
