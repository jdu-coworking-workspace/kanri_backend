# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
def root():
    return {"message":"Cowork API is running"}

app.include_router(api_router, prefix="/api/v1")