# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str
    PORT: int = 8000
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 1440
    COOKIE_NAME: str = "access_token"
    CORS_ORIGIN: str

    class Config:
        env_file = ".env"

settings = Settings()