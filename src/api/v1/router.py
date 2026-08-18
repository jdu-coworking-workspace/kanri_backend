# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from src.api.v1 import auth, student

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(student.router, prefix="/students", tags=["Students"])
