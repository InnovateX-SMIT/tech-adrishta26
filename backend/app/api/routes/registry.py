from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.app.models.registry import (
    MemberStatusResponse,
    RegisterMemberRequest,
    RescueMember,
)
from backend.app.services.registry_service import (
    MemberAlreadyRevokedError,
    MemberNotFoundError,
    registry_service,
)

router = APIRouter(prefix="/registry")


@router.get("/members", response_model=List[RescueMember])
async def list_members() -> List[RescueMember]:
    """Retrieves all registered rescue team members (active and revoked)."""
    return registry_service.get_all_members()


@router.post("/members", response_model=RescueMember, status_code=status.HTTP_201_CREATED)
async def register_member(request: RegisterMemberRequest) -> RescueMember:
    """Registers a new rescue team member with auto-generated unique IDs and active status.

    Rejects unknown or private key fields with HTTP 422.
    """
    try:
        return registry_service.register_member(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register rescue member: {str(exc)}",
        )


@router.get("/members/{rescue_id}", response_model=RescueMember)
async def get_member_by_rescue_id(rescue_id: str) -> RescueMember:
    """Finds a member by exact Rescue ID."""
    member = registry_service.get_member_by_rescue_id(rescue_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rescue member '{rescue_id}' not found in registry.",
        )
    return member


@router.get("/devices/{device_id}", response_model=RescueMember)
async def get_member_by_device_id(device_id: str) -> RescueMember:
    """Finds a member by associated administrative Device ID."""
    member = registry_service.get_member_by_device_id(device_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device record '{device_id}' not found in registry.",
        )
    return member


@router.get("/members/{rescue_id}/status", response_model=MemberStatusResponse)
async def get_member_status(rescue_id: str) -> MemberStatusResponse:
    """Checks the active status of a registered rescue member."""
    member = registry_service.get_member_by_rescue_id(rescue_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rescue member '{rescue_id}' not found in registry.",
        )
    return MemberStatusResponse(
        rescue_id=member.rescue_id,
        status=member.status,
        is_active=registry_service.is_member_active(rescue_id),
    )


@router.post("/members/{rescue_id}/revoke", response_model=MemberStatusResponse)
async def revoke_member(rescue_id: str) -> MemberStatusResponse:
    """Revokes a rescue member's active status while preserving the historical record.

    Returns HTTP 409 Conflict if the member is already revoked.
    """
    try:
        updated = registry_service.revoke_member(rescue_id)
        return MemberStatusResponse(
            rescue_id=updated.rescue_id,
            status=updated.status,
            is_active=False,
        )
    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rescue member '{rescue_id}' not found in registry.",
        )
    except MemberAlreadyRevokedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rescue member '{rescue_id}' is already revoked.",
        )
