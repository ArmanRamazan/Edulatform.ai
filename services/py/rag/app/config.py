from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5439/rag_db"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768
    chunk_size: int = 1000
    chunk_overlap: int = 200
    github_token: str = ""
    embedding_service_url: str = ""
    qdrant_url: str = ""
    qdrant_collection: str = "rag_chunks"
