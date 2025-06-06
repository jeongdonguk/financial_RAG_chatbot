from pydantic_settings import BaseSettings,SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8"
    )
    