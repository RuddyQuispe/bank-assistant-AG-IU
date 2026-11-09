from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document


def get_content_pdf_file(file_path: Path) -> list[Document]:
    """load content pdf file (only text)"""
    loader: PyPDFLoader = PyPDFLoader(file_path=str(file_path))
    documents: list[Document] = loader.load()
    for document in documents:
        document.metadata["file_name"] = file_path.name
        document.metadata["file_type"] = "pdf"
    return documents


def get_content_txt_file(file_path: Path) -> list[Document]:
    """load content txt file (only text)"""
    loader: TextLoader = TextLoader(file_path=str(file_path), encoding="utf-8")
    documents: list[Document] = loader.load()
    for document in documents:
        document.metadata["file_name"] = file_path.name
        document.metadata["file_type"] = "txt"
        document.metadata["source"] = str(file_path)
    return documents
