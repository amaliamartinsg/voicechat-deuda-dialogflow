import os
from dataclasses import dataclass
from qdrant_client import QdrantClient

from dotenv import load_dotenv
load_dotenv()


@dataclass
class Settings:
    # Qdrant Configuration
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "clients_info_energix")
    persist_db_dir: str = os.getenv("DB_DIR", "src/rag/vector_db")

    # LLM Configuration
    llm_model_name: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    # Embedding Configuration
    embedding_model_name: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # General Configuration
    threshold: float = float(os.getenv("THRESHOLD", "0.82"))
    k_docs: int = int(os.getenv("K_DOCS", 3))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    qdrant_client = QdrantClient(url=qdrant_url)

SETTINGS = Settings()