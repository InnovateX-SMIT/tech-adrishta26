from fastapi import APIRouter
from backend.app.config import settings
from backend.app.models.schemas import SystemInfoResponse

router = APIRouter(prefix="/system")


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        project=settings.project_name,
        mode=settings.environment,
        mesh_enabled=settings.mesh_enabled,
        encryption_enabled=settings.encryption_enabled,
        phase=settings.phase,
    )
