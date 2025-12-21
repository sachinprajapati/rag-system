from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # FastAPI settings
    API_TITLE: str = Field(default="RAG System API", description="API title")
    API_VERSION: str = Field(default="1.0.0", description="API version")
    API_DESCRIPTION: str = Field(
        default="Production-Grade Retrieval-Augmented Generation API",
        description="API description"
    )
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    
    # FAISS settings
    FAISS_INDEX_PATH: str = Field(
        default="./faiss_index",
        description="Path to FAISS index directory"
    )
    
    # Document settings
    DOCUMENT_UPLOAD_PATH: str = Field(
        default="./uploads",
        description="Path to uploaded documents"
    )
    
    # Embedding model
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model for embeddings"
    )
    
    # Text splitter settings
    CHUNK_SIZE: int = Field(default=512, description="Text chunk size")
    CHUNK_OVERLAP: int = Field(default=50, description="Text chunk overlap")
    
    # Generation settings
    MAX_TOKENS: int = Field(default=512, description="Max tokens for generation")
    TEMPERATURE: float = Field(default=0.7, description="Temperature for generation")
    
    # Keycloak OAuth2/OIDC settings
    KEYCLOAK_URL: str = Field(
        default="http://localhost:8080",
        description="Keycloak server URL"
    )
    KEYCLOAK_REALM: str = Field(
        default="rag-system",
        description="Keycloak realm name"
    )
    KEYCLOAK_CLIENT_ID: str = Field(
        default="rag-backend",
        description="Keycloak client ID for backend"
    )
    KEYCLOAK_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="Keycloak client secret (if using confidential client)"
    )
    
    # Authentication settings
    AUTH_ENABLED: bool = Field(
        default=False,
        description="Enable/disable authentication - set to True or use AUTH_ENABLED=true in .env"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }

settings = Settings()