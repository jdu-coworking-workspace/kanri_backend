# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings
from typing import Literal, Optional


class Settings(BaseSettings):
    APP_ENV: str
    PORT: int = 8000
    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 1440
    COOKIE_NAME: str = "access_token"
    CORS_ORIGIN: str

    # Storage mode: "local" yoki "production"
    S3_MODE: Literal["local", "production"] = "local"

    # AWS S3 (faqat S3_MODE=production bo'lganda ishlatiladi)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-northeast-1"
    AWS_S3_BUCKET_NAME: str = ""

    class Config:
        env_file = ".env"


settings = Settings()