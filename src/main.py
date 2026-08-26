from pathlib import Path

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.api.v1.router import api_router

app = FastAPI(
    title="Cowork Management API",
    description="Backend for managing projects and students",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local rejimda: backend/media/ papkasini /media URL orqali serve qilamiz
if settings.S3_MODE == "local":
    MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.get("/")
def root():
    return {"message": "Cowork API is running"}


app.include_router(api_router, prefix="/api/v1")