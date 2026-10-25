import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class LangChainSettings:
    """ settings environments """
    # api y documentación (equivalente a springdoc en application.yml)
    API_TITLE: str = os.getenv("API_TITLE", "Digital Wallet RAG")
    API_VERSION: str = os.getenv("API_VERSION", "0.1.0")
    API_DESCRIPTION: str = "Asistente de banca móvil con RAG sobre documentos de bancos de Bolivia."
    # en producción: DOCS_ENABLED=false apaga /docs, /redoc, /openapi.json y Scalar
    DOCS_ENABLED: bool = os.getenv("DOCS_ENABLED", "true").lower() == "true"
    SCALAR_PATH: str = os.getenv("SCALAR_PATH", "/scalar")
    SCALAR_THEME: str = os.getenv("SCALAR_THEME", "default")
    CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL")
    EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL")
    DEFAULT_TEMPERATURE: float | int = 0.7
    LOW_TOMPERATURE: float | int = 0.1
    MAX_RETRIES: int = 3
    # chroma settings
    CHROMA_PATH: Path = Path("./data/langchain_chroma")
    CHROMA_COLLECTION: str = "agent-bank-rag"
    DOCUMENTS_DIR = Path("data/documents")
    # files extension supported
    SUPPORTED_EXTENSION = {".txt", ".pdf"}
    # rag config
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 3
    # memoria del grafo: "sqlite" o "postgres"
    MEMORY_BACKEND: str = "sqlite"
    SQLITE_DB_PATH: Path = Path("./data/memory.db")
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    # auth (JWT)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "digital-wallet-rqm"
    JWT_EXPIRE_MINUTES: int = 60
    # usuario de demo mientras no exista una base de usuarios
    DEMO_USER_ID: str = "1"
    DEMO_USER_NICKNAME: str = "ruddy"
    # approx cost
    COST_INPUT_PER_MILLION: float = 0.15
    COST_OUTPUT_PER_MILLION: float = 0.60

    @classmethod
    def validate(cls) -> None:
        """Valida variables criticas"""
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("MODEL_")


settings = LangChainSettings()
