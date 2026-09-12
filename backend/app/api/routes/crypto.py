from fastapi import APIRouter, HTTPException, status
from backend.app.models.crypto import (
    DeviceCryptoInitResponse,
    DeviceCryptoStatusResponse,
)
from backend.app.services.crypto_service import (
    CriticalConsistencyError,
    CryptoServiceError,
    DeviceAlreadyInitializedError,
    DeviceRevokedError,
    InconsistentKeyStateError,
    crypto_service,
)
from backend.app.services.registry_service import MemberNotFoundError

router = APIRouter(prefix="/crypto")


@router.post(
    "/devices/{device_id}/initialize",
    response_model=DeviceCryptoInitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def initialize_device_keys(device_id: str) -> DeviceCryptoInitResponse:
    """Initializes long-term cryptographic keypairs (Ed25519 & X25519) for a registered device.

    Saves private keys locally in backend storage and registers public keys in registry.
    Returns only safe public metadata without exposing private keys.
    """
    try:
        return crypto_service.initialize_device_keys(device_id)
    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found in registry.",
        )
    except DeviceRevokedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except DeviceAlreadyInitializedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except InconsistentKeyStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except CriticalConsistencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical storage failure: {exc}",
        )
    except CryptoServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize device keys: {exc}",
        )


@router.get(
    "/devices/{device_id}/status",
    response_model=DeviceCryptoStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_device_crypto_status(device_id: str) -> DeviceCryptoStatusResponse:
    """Returns the public cryptographic readiness status for a device."""
    try:
        return crypto_service.get_device_crypto_status(device_id)
    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found in registry.",
        )
