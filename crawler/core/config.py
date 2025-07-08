from pydantic_settings import BaseSettings,SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str
    MONGODB_URL: str
    MONGODB_DATABASE: str
    MONGODB_COLLECTION: str
    
    # PDF 다운로드 설정
    PDF_DOWNLOAD_TIMEOUT: int
    PDF_MAX_SIZE_MB: int
    
    # OpenAI API 설정
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_MAX_TOKENS: int
    OPENAI_TEMPERATURE: float

    FUND_PDF_URL: str

    # Qdrant 설정
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "fund_documents"
    
    # 임베딩 모델 설정
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 512

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8"
    )
    