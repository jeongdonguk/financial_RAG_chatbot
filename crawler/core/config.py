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

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8"
    )
    