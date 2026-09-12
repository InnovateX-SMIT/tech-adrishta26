from fastapi import APIRouter, HTTPException, status

from backend.app.models.dashboard import (
    DashboardOverviewResponse,
    QuickDispatchRequest,
    QuickDispatchResponse,
)
from backend.app.services.dashboard_service import dashboard_service

router = APIRouter()


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get real-time dashboard telemetry overview",
    description=(
        "Returns the unified state of the RESQ system: operational blackout status, "
        "live mesh topology, active routing path, messaging metrics, security authority, "
        "and packet-sniffing attacker observations."
    ),
)
async def get_dashboard_overview() -> DashboardOverviewResponse:
    try:
        return dashboard_service.get_overview()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile dashboard telemetry: {str(exc)}",
        )


@router.post(
    "/quick-dispatch",
    response_model=QuickDispatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Atomic emergency quick-dispatch from Dashboard",
    description=(
        "Dispatches an emergency distress dispatch across the mesh network, evaluates the attacker tap, "
        "verifies the receiver authorization gate, and returns the refreshed telemetry overview in one atomic call."
    ),
)
async def dashboard_quick_dispatch(request: QuickDispatchRequest) -> QuickDispatchResponse:
    try:
        return dashboard_service.quick_dispatch(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quick dispatch failed: {str(exc)}",
        )
