# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from src.api.v1 import auth, student, project, user, uploads

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(student.router, prefix="/students", tags=["Students"])
api_router.include_router(project.router, prefix="/projects", tags=["Projects"])
api_router.include_router(user.router, prefix="/users", tags=["Users"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
