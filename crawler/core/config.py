import pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env_file = ".env"
    env_file_encoding = "utf-8"

    DATABASE_URL: str
    