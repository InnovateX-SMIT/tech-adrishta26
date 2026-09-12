from fastapi import APIRouter
from .health import router as health_router
from .system import router as system_router
from .registry import router as registry_router
from .crypto import router as crypto_router
from .mesh import router as mesh_router
from .messages import router as messages_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(system_router, tags=["System"])
api_router.include_router(registry_router, tags=["Registry"])
api_router.include_router(crypto_router, tags=["Crypto"])
api_router.include_router(mesh_router, prefix="/mesh", tags=["Mesh"])
api_router.include_router(messages_router, prefix="/messages", tags=["Messages"])

__all__ = ["api_router"]

