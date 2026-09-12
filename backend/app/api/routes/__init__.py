from typing import List
from fastapi import APIRouter
from backend.app.models.messages import ConversationResponse, MessageRecord
from backend.app.services.message_service import message_service
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


@api_router.get(
    "/conversations/{device_a}/{device_b}",
    response_model=ConversationResponse,
    tags=["Messages"],
    summary="Get conversation between two devices (Top-level endpoint)",
)
async def get_conversation_toplevel(device_a: str, device_b: str) -> ConversationResponse:
    return message_service.get_conversation_thread(device_a, device_b)


@api_router.get(
    "/devices/{device_id}/messages",
    response_model=List[MessageRecord],
    tags=["Messages"],
    summary="Get message history for device (Top-level endpoint)",
)
async def get_device_messages_toplevel(device_id: str) -> List[MessageRecord]:
    return message_service.list_device_messages(device_id)


__all__ = ["api_router"]


