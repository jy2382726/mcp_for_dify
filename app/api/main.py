from fastapi import APIRouter
from app.api.routes import minio

api_router = APIRouter()
api_router.include_router(minio.router, prefix="/minio", tags=["minio"])
