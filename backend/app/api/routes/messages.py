from typing import List
from fastapi import APIRouter, HTTPException, status

from backend.app.core.crypto import CryptoError
from backend.app.core.mesh_network import NoRouteError
from backend.app.core.message_repository import MessageNotFoundError
from backend.app.models.messages import (
    ConversationResponse,
    DecryptMessageRequest,
    DecryptMessageResponse,
    InboxMessageSummary,
    MessageRecord,
    MessageStatusResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from backend.app.services.crypto_service import CryptoServiceError
from backend.app.services.message_service import (
    MemberMissingKeysError,
    MemberNotActiveError,
    MeshNodeNotFoundError,
    MessageServiceError,
    PacketNotFoundError,
    message_service,
)
from backend.app.services.registry_service import MemberNotFoundError

router = APIRouter()


def _handle_send_message(body: SendMessageRequest) -> SendMessageResponse:
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


@router.post(
    "",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send secure emergency message (Canonical)",
    description=(
        "Canonical endpoint: Encrypts the emergency message using X25519 + ChaCha20-Poly1305, "
        "signs canonical metadata and ciphertext with sender's Ed25519 key, and transmits the secure "
        "packet across the mesh network. The transmitted packet payload NEVER contains plaintext."
    ),
)
async def send_secure_message_canonical(body: SendMessageRequest) -> SendMessageResponse:
    return _handle_send_message(body)


@router.post(
    "/send",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send secure emergency message (Alias)",
    description="Delegates directly to canonical send_secure_message without duplicate logic.",
)
async def send_secure_message_alias(body: SendMessageRequest) -> SendMessageResponse:
    return _handle_send_message(body)


@router.get(
    "/conversations/{device_a}/{device_b}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation thread between two devices",
)
async def get_conversation(device_a: str, device_b: str) -> ConversationResponse:
    return message_service.get_conversation_thread(device_a, device_b)


@router.get(
    "/device/{device_id}",
    response_model=List[MessageRecord],
    status_code=status.HTTP_200_OK,
    summary="Get message history for device",
)
async def get_device_messages(device_id: str) -> List[MessageRecord]:
    return message_service.list_device_messages(device_id)


@router.get(
    "/{message_id}",
    response_model=MessageRecord,
    status_code=status.HTTP_200_OK,
    summary="Get secure message record by ID (No plaintext)",
)
async def get_message_record(message_id: str) -> MessageRecord:
    record = message_service.get_message(message_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message '{message_id}' not found.",
        )
    return record


@router.get(
    "/{message_id}/status",
    response_model=MessageStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get message delivery lifecycle status",
)
async def get_message_status(message_id: str) -> MessageStatusResponse:
    try:
        return message_service.get_message_status(message_id)
    except MessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/{message_id}/retry",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry a failed or queued message without duplicating plaintext",
)
async def retry_message(message_id: str) -> SendMessageResponse:
    try:
        return message_service.retry_failed_message(message_id)
    except MessageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
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
    except (MemberNotActiveError, MemberMissingKeysError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except NoRouteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No route found during retry: {str(exc)}",
        )
    except MessageServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry message: {str(exc)}",
        )



@router.get(
    "/inbox/{recipient_id}",
    response_model=List[InboxMessageSummary],
    status_code=status.HTTP_200_OK,
    summary="Get recipient device inbox",
    description="Retrieve encrypted packets delivered to the recipient node's mesh inbox. Contains no plaintext.",
)
async def get_device_inbox(recipient_id: str) -> List[InboxMessageSummary]:
    try:
        return message_service.get_inbox_messages(recipient_id=recipient_id)
    except MemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query device inbox: {str(exc)}",
        )


@router.post(
    "/decrypt",
    response_model=DecryptMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Authorize and decrypt emergency message (Phase 6)",
    description=(
        "Processes an incoming encrypted packet through the Phase 6 authorization gate: "
        "validates sender identity in registry, verifies active status, verifies Ed25519 digital signature, "
        "enforces recipient device authorization, checks replay protection, and executes ChaCha20-Poly1305 "
        "AEAD decryption. Plaintext is released only if all checks pass."
    ),
)
async def decrypt_message(body: DecryptMessageRequest) -> DecryptMessageResponse:
    try:
        if body.packet_id:
            return message_service.decrypt_inbox_message(
                recipient_id=body.recipient_id,
                packet_id=body.packet_id,
            )
        elif body.payload:
            return message_service.decrypt_direct_payload(
                recipient_id=body.recipient_id,
                payload=body.payload,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'packet_id' or 'payload' must be provided in DecryptMessageRequest.",
            )
    except MemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except PacketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except MeshNodeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except CryptoServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cryptographic error: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process decryption: {str(exc)}",
        )


@router.get(
    "/security-logs",
    response_model=List[dict],
    status_code=status.HTTP_200_OK,
    summary="Get security authorization gate audit logs (No plaintext)",
)
async def get_security_logs() -> List[dict]:
    from backend.app.core.decryption_gate import SECURITY_LOGS
    return list(SECURITY_LOGS)

