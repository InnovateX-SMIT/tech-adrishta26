from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from backend.app.models.attack import (
    AttackStatusResponse,
    CapturedPacket,
    SimulateAttackRequest,
    SimulateAttackResponse,
    TamperCaptureRequest,
    TamperCaptureResponse,
)
from backend.app.services.attack_simulation_service import attack_simulation_service

router = APIRouter()


@router.post(
    "/simulate",
    response_model=SimulateAttackResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute packet-sniffing attack simulation (Contrast Mode)",
    description=(
        "Executes a transmission through the simulated mesh in either 'vulnerable' (unencrypted) "
        "or 'protected' (X25519 + ChaCha20-Poly1305 + Ed25519) mode, demonstrating how an eavesdropper "
        "can read unencrypted packets but cannot read protected packets."
    ),
)
async def simulate_attack(request: SimulateAttackRequest) -> SimulateAttackResponse:
    try:
        return attack_simulation_service.simulate_attack(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation failed: {str(exc)}",
        )


@router.post(
    "/captures/{capture_id}/tamper",
    response_model=TamperCaptureResponse,
    status_code=status.HTTP_200_OK,
    summary="Tamper with a captured packet and verify receiver rejection",
    description="Mutates a byte in the captured ciphertext or signature and feeds it to the receiver gate to verify rejection.",
)
async def tamper_captured_packet(
    capture_id: str,
    request: TamperCaptureRequest,
) -> TamperCaptureResponse:
    try:
        return attack_simulation_service.tamper_capture(
            capture_id=capture_id,
            tamper_field=request.tamper_field,
            recipient_id=request.recipient_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tampering simulation error: {str(exc)}",
        )


@router.get(
    "/captures",
    response_model=List[CapturedPacket],
    status_code=status.HTTP_200_OK,
    summary="List captured packets from simulation",
    description="Returns the history of captured packets from the passive attacker node.",
)
async def list_captures() -> List[CapturedPacket]:
    return attack_simulation_service.list_captures()


@router.get(
    "/captures/{capture_id}",
    response_model=CapturedPacket,
    status_code=status.HTTP_200_OK,
    summary="Get a specific captured packet record",
)
async def get_capture(capture_id: str) -> CapturedPacket:
    record = attack_simulation_service.get_capture_by_id(capture_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture record '{capture_id}' not found.",
        )
    return record


@router.get(
    "/status",
    response_model=AttackStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current attack simulation statistics",
)
async def get_attack_status() -> AttackStatusResponse:
    return attack_simulation_service.get_status()


@router.post(
    "/reset",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reset Phase 7 attack simulation state",
    description="Clears captured packets and simulation logs while strictly preserving identities and cryptographic keys.",
)
async def reset_attack_simulation() -> Dict[str, Any]:
    return attack_simulation_service.reset_simulation()
