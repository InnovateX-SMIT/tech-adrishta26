from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.schemas import HopRecordSchema


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
