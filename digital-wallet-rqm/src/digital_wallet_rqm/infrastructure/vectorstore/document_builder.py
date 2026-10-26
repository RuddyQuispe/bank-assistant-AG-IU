from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.infrastructure.vectorstore.document_loaders import get_content_pdf_file, get_content_txt_file


def load_file(file_path: Path) -> list[Document]:
    if not file_path.exists():
        raise FileNotFoundError(f"File {file_path} does not exist")
    extension = file_path.suffix.lower()
    if extension not in settings.SUPPORTED_EXTENSION:
        raise ValueError(f"File {file_path} does not have supported extension")
    docs: list[Document] = []
    if extension == ".pdf":
        docs = get_content_pdf_file(file_path)
    elif extension == ".txt":
        docs = get_content_txt_file(file_path)
    print(f"loaded {len(docs)} documents")
    return docs


def load_directory_files(directory_path: Path) -> list[Document]:
    if not directory_path.exists():
        directory_path.mkdir(parents=True, exist_ok=True)
        print(f"created directory {directory_path}"
              f"Add files {settings.SUPPORTED_EXTENSION} to {directory_path}")
        return []
    all_files: list = []
    for extensions in settings.SUPPORTED_EXTENSION:
        all_files.extend(directory_path.glob(f"*{extensions}"))
        all_files.extend(directory_path.glob(f"*{extensions.upper()}"))
    all_files = list(set(all_files))
    all_docs: list = []
    for file_path in sorted(all_files):
        docs = load_file(file_path=file_path)
        all_docs.extend(docs)
    return all_docs


def split_documents(docs: list[Document], chunk_size: int = settings.CHUNK_SIZE,
                    chunk_overlap: int = settings.CHUNK_OVERLAP) -> list[Document]:
    splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True
    )
    chunks = splitter.split_documents(docs)
    print(f"{len(docs)} seccion/es -> {len(chunks)} chunks"
          f"(tamaño: ~{chunk_size} chars,"
          f"overlap: {chunk_overlap})")
    return chunks


def make_chunk_ids(chunks: list[Document]) -> list[str]:
    """Crea un id fijo por chunk: archivo:pagina:inicio (ej. "manual.pdf:3:120").

    Con el mismo archivo se generan los mismos ids, asi volver a indexar pisa en vez de duplicar.
    """
    ids = []
    for chunk in chunks:
        file_name = chunk.metadata["file_name"]
        page = chunk.metadata.get("page", 0)  # los .txt no tienen pagina
        start_index = chunk.metadata["start_index"]
        ids.append(f"{file_name}:{page}:{start_index}")
    return ids
