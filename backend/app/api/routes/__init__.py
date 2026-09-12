from fastapi import APIRouter
from .health import router as health_router
from .system import router as system_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(system_router, tags=["System"])

__all__ = ["api_router"]
