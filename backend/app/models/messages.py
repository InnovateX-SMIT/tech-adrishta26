from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.schemas import HopRecordSchema


class MessageStatus(str, Enum):
    """Strict Phase 5 message lifecycle statuses."""
    CREATED = "CREATED"
    ENCRYPTED = "ENCRYPTED"
    QUEUED = "QUEUED"
    ROUTING = "ROUTING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    DECRYPTED = "DECRYPTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


def build_conversation_id(device_a: str, device_b: str) -> str:
    """Generates deterministic canonical conversation identifier between two devices."""
    first, second = sorted([device_a.strip().upper(), device_b.strip().upper()])
    return f"CONV_{first}_{second}"


class SendMessageRequest(BaseModel):
    """Request model for composing and dispatching a secure emergency message."""
    model_config = ConfigDict(extra="forbid")

    sender_id: str = Field(
        ...,
        min_length=1,
        description="Sender Rescue ID (e.g. RESQ-001) or Device ID (e.g. DEVICE-001)",
        examples=["RESQ-001"],
    )
    recipient_id: str = Field(
        ...,
        min_length=1,
        description="Recipient Rescue ID (e.g. RESQ-002) or Device ID (e.g. DEVICE-002)",
        examples=["RESQ-002"],
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Plaintext emergency message to be encrypted and transmitted",
        examples=["SOS: Medic needed at Sector 4."],
    )
    priority: Optional[str] = Field(
        "NORMAL",
        description="Transmission priority level (e.g. NORMAL, HIGH, CRITICAL)",
        examples=["HIGH"],
    )


class SecureMessagePayload(BaseModel):
    """Encrypted and signed message container transmitted across the mesh.

    Guarantees:
    - NEVER contains plaintext message content.
    - Encapsulates X25519 + ChaCha20-Poly1305 AEAD parameters.
    - Contains Ed25519 signature over canonical metadata + ciphertext.
    """
    model_config = ConfigDict(extra="forbid")

    version: int = Field(1, description="Protocol version", examples=[1])
    packet_id: str = Field(..., description="Unique packet tracking ID", examples=["PKT-1001"])
    message_id: str = Field(..., description="Unique emergency message ID", examples=["MSG-1001"])
    sender_rescue_id: str = Field(..., description="Sender administrative ID", examples=["RESQ-001"])
    sender_device_id: str = Field(..., description="Sender cryptographic/mesh device ID", examples=["DEVICE-001"])
    recipient_rescue_id: str = Field(..., description="Recipient administrative ID", examples=["RESQ-002"])
    recipient_device_id: str = Field(..., description="Recipient cryptographic/mesh device ID", examples=["DEVICE-002"])
    timestamp: int = Field(..., description="Deterministic integer UTC Unix timestamp", examples=[1789210000])
    key_agreement: str = Field("X25519", description="Key exchange algorithm", examples=["X25519"])
    kdf: str = Field("HKDF-SHA256", description="Key derivation function", examples=["HKDF-SHA256"])
    cipher: str = Field("ChaCha20-Poly1305", description="Authenticated symmetric cipher", examples=["ChaCha20-Poly1305"])
    ephemeral_public_key: str = Field(..., description="Base64 raw 32-byte X25519 ephemeral public key")
    salt: str = Field(..., description="Base64 16-byte HKDF salt")
    nonce: str = Field(..., description="Base64 12-byte ChaCha20-Poly1305 nonce")
    ciphertext: str = Field(..., description="Base64 ciphertext including 16-byte Poly1305 authentication tag")
    signature: str = Field(..., description="Base64 64-byte Ed25519 signature over canonical dictionary")


class SendMessageResponse(BaseModel):
    """Response returned after successful encryption, signing, and mesh dispatch."""
    packet_id: str = Field(..., examples=["PKT-1001"])
    message_id: str = Field(..., examples=["MSG-1001"])
    sender_id: str = Field(..., examples=["RESQ-001"])
    recipient_id: str = Field(..., examples=["RESQ-002"])
    status: str = Field("delivered", examples=["delivered"])
    hop_log: List[HopRecordSchema] = Field(default_factory=list)
    payload: SecureMessagePayload


class DecryptMessageRequest(BaseModel):
    """Request model for Phase 6 controlled authorization and decryption."""
    model_config = ConfigDict(extra="forbid")

    recipient_id: str = Field(
        ...,
        min_length=1,
        description="Recipient Rescue ID (e.g. RESQ-002) or Device ID (e.g. DEVICE-002) performing decryption",
        examples=["RESQ-002"],
    )
    packet_id: Optional[str] = Field(
        None,
        description="Unique packet ID to locate in the recipient device's inbox",
        examples=["PKT-1001"],
    )
    payload: Optional[SecureMessagePayload] = Field(
        None,
        description="Optional direct SecureMessagePayload to authorize and decrypt",
    )


class DecryptMessageResponse(BaseModel):
    """Response returned by the Phase 6 authorization & decryption gate."""
    status: str = Field(..., description="'SUCCESS' or 'REJECTED'", examples=["SUCCESS"])
    message: Optional[str] = Field(None, description="Decrypted plaintext released only on authorization success")
    sender_name: Optional[str] = Field(None, description="Authenticated sender name from registry")
    sender_id: Optional[str] = Field(None, description="Authenticated sender Rescue ID")
    packet_id: Optional[str] = Field(None, description="Packet ID processed")
    message_id: Optional[str] = Field(None, description="Message ID processed")
    reason: Optional[str] = Field(None, description="Controlled rejection reason if authorization or decryption failed")
    detail: Optional[str] = Field(None, description="Human-readable security reason")



class InboxMessageSummary(BaseModel):
    """Encrypted packet summary sitting in a device's inbox awaiting authorization."""
    packet_id: str = Field(..., examples=["PKT-1001"])
    message_id: str = Field(..., examples=["MSG-1001"])
    sender_rescue_id: str = Field(..., examples=["RESQ-001"])
    sender_device_id: str = Field(..., examples=["DEVICE-001"])
    recipient_rescue_id: str = Field(..., examples=["RESQ-002"])
    recipient_device_id: str = Field(..., examples=["DEVICE-002"])
    timestamp: int = Field(..., examples=[1789210000])
    status: str = Field("encrypted", examples=["encrypted"])
    payload: SecureMessagePayload


class MessageRecord(BaseModel):
    """Persistent representation of a secure message on disk.

    SECURITY GUARANTEE:
    Contains strictly ZERO plaintext content.
    Only the authenticated encryption envelope (ciphertext, nonce, salt, ephemeral pubkey, signature)
    and routing metadata are persisted.
    """
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(..., description="Unique emergency message ID", examples=["MSG-1001"])
    packet_id: str = Field(..., description="Active or latest mesh packet tracking ID", examples=["PKT-1001"])
    sender_device_id: str = Field(..., description="Sender device ID", examples=["DEVICE-001"])
    recipient_device_id: str = Field(..., description="Recipient device ID", examples=["DEVICE-002"])
    sender_rescue_id: str = Field(..., description="Sender Rescue ID", examples=["RESQ-001"])
    recipient_rescue_id: str = Field(..., description="Recipient Rescue ID", examples=["RESQ-002"])
    conversation_id: str = Field(..., description="Canonical bidirectional conversation ID", examples=["CONV_DEVICE-001_DEVICE-002"])
    created_at: float = Field(..., description="Creation Unix timestamp")
    delivered_at: Optional[float] = Field(None, description="Delivery Unix timestamp")
    decrypted_at: Optional[float] = Field(None, description="Decryption Unix timestamp")
    status: MessageStatus = Field(MessageStatus.CREATED, description="Current lifecycle status")
    failure_reason: Optional[str] = Field(None, description="Failure reason if delivery or decryption failed")
    retry_count: int = Field(0, description="Number of delivery retries attempted")
    hop_count: int = Field(0, description="Hops traversed through mesh network")
    route: List[str] = Field(default_factory=list, description="Mesh route nodes traversed")
    payload: SecureMessagePayload = Field(..., description="Encrypted and signed message envelope (NO PLAINTEXT)")


class MessageStatusResponse(BaseModel):
    """Status tracking response for a message."""
    message_id: str
    packet_id: str
    sender_id: str
    recipient_id: str
    status: MessageStatus
    created_at: float
    delivered_at: Optional[float] = None
    decrypted_at: Optional[float] = None
    retry_count: int = 0
    hop_count: int = 0
    route: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation thread response between two devices."""
    conversation_id: str
    device_a: str
    device_b: str
    total_messages: int
    messages: List[MessageRecord]
