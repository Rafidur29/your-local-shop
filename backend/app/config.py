from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./dev.db"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-this-secret"
    FRONTEND_ORIGINS: List[str] = ["http://localhost:3000"]
    PAYMENT_MOCK_DELAY_MS: int = 200
    RESERVATION_TTL_SECONDS: int = 900

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
