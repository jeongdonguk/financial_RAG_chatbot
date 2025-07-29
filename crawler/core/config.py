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

    # Qdrant 설정 (환경변수에서 읽어옴)
    QDRANT_URL: str
    QDRANT_API_KEY: str
    QDRANT_COLLECTION_NAME: str
    
    # 임베딩 모델 설정
    EMBEDDING_MODEL_NAME: str
    EMBEDDING_DIMENSION: int
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8"
    )
    