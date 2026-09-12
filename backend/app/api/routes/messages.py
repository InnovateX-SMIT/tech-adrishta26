from fastapi import APIRouter, HTTPException, status

from backend.app.core.crypto import CryptoError
from backend.app.core.mesh_network import NoRouteError
from backend.app.models.messages import SendMessageRequest, SendMessageResponse
from backend.app.services.crypto_service import CryptoServiceError
from backend.app.services.message_service import (
    MemberMissingKeysError,
    MemberNotActiveError,
    MeshNodeNotFoundError,
    MessageServiceError,
    message_service,
)
from backend.app.services.registry_service import MemberNotFoundError

router = APIRouter()


@router.post(
    "/send",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send secure emergency message",
    description=(
        "Encrypts the emergency message using X25519 + ChaCha20-Poly1305, signs the canonical "
        "metadata and ciphertext with the sender's Ed25519 key, and transmits the secure packet "
        "across the mesh network. The transmitted packet payload NEVER contains plaintext."
    ),
)
async def send_secure_message(body: SendMessageRequest) -> SendMessageResponse:
    try:
        return message_service.send_secure_message(
            sender_id=body.sender_id,
            recipient_id=body.recipient_id,
            message=body.message,
            priority=body.priority or "NORMAL",
        )
    except MemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except MeshNodeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except MemberNotActiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except MemberMissingKeysError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except CryptoServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cryptographic key error: {str(exc)}",
        )
    except NoRouteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No route found in mesh network: {str(exc)}",
        )
    except CryptoError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cryptographic failure: {str(exc)}",
        )
    except MessageServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transmit secure message: {str(exc)}",
        )
