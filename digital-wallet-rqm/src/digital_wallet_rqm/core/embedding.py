import os
from pathlib import Path

from langchain_chroma import Chroma

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.core.llm_model import get_llm_embedding


def get_or_create_vector_store(collection_name: str, persist_path: Path = settings.CHROMA_PATH) -> Chroma:
    """create or get saved vector store"""
    os.makedirs(persist_path, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_llm_embedding(),
        persist_directory=str(persist_path)
    )
