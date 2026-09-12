from fastapi import APIRouter
from backend.app.config import settings
from backend.app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        phase=settings.phase_name,
    )
