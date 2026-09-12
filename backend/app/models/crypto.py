import base64
from typing import Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class EncryptionEnvelope(BaseModel):
    """Authenticated encryption envelope for ReSQ peer-to-peer payloads.

    Contains cryptographic parameters required for X25519 key agreement,
    HKDF-SHA256 key derivation, and ChaCha20-Poly1305 authenticated decryption.
    """
    model_config = ConfigDict(extra="forbid")

    version: int = Field(1, examples=[1])
    key_agreement: Literal["X25519"] = "X25519"
    kdf: Literal["HKDF-SHA256"] = "HKDF-SHA256"
    cipher: Literal["ChaCha20-Poly1305"] = "ChaCha20-Poly1305"
    ephemeral_public_key: str = Field(..., description="Base64-encoded raw 32-byte X25519 ephemeral public key")
    salt: str = Field(..., description="Base64-encoded 16-byte random HKDF salt")
    nonce: str = Field(..., description="Base64-encoded 12-byte ChaCha20-Poly1305 nonce")
    ciphertext: str = Field(..., description="Base64-encoded ciphertext including 16-byte Poly1305 auth tag")
    associated_data: Optional[str] = Field(None, description="Optional Base64-encoded caller associated data")

    @field_validator("ephemeral_public_key")
    @classmethod
    def validate_ephemeral_key(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v)
            if len(raw) != 32:
                raise ValueError("Ephemeral public key must decode to exactly 32 bytes.")
        except Exception as exc:
            raise ValueError(f"Invalid ephemeral public key Base64: {exc}") from exc
        return v

    @field_validator("salt")
    @classmethod
    def validate_salt(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v)
            if len(raw) != 16:
                raise ValueError("Salt must decode to exactly 16 bytes.")
        except Exception as exc:
            raise ValueError(f"Invalid salt Base64: {exc}") from exc
        return v

    @field_validator("nonce")
    @classmethod
    def validate_nonce(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v)
            if len(raw) != 12:
                raise ValueError("Nonce must decode to exactly 12 bytes.")
        except Exception as exc:
            raise ValueError(f"Invalid nonce Base64: {exc}") from exc
        return v

    @field_validator("ciphertext")
    @classmethod
    def validate_ciphertext(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v)
            if len(raw) < 16:
                raise ValueError("Ciphertext must contain at least 16 bytes (Poly1305 authentication tag).")
        except Exception as exc:
            raise ValueError(f"Invalid ciphertext Base64: {exc}") from exc
        return v

    @field_validator("associated_data")
    @classmethod
    def validate_associated_data(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                base64.b64decode(v)
            except Exception as exc:
                raise ValueError(f"Invalid associated_data Base64: {exc}") from exc
        return v


class DeviceCryptoInitResponse(BaseModel):
    """Safe public metadata returned upon successful device key initialization."""
    device_id: str = Field(..., examples=["DEVICE-001"])
    rescue_id: str = Field(..., examples=["RESQ-001"])
    signing_public_key: str = Field(..., description="Base64 Ed25519 public key")
    encryption_public_key: str = Field(..., description="Base64 X25519 public key")
    status: str = Field("initialized", examples=["initialized"])
    algorithms: Dict[str, str] = Field(
        default_factory=lambda: {
            "signature": "Ed25519",
            "key_agreement": "X25519",
            "kdf": "HKDF-SHA256",
            "authenticated_cipher": "ChaCha20-Poly1305",
        }
    )


class DeviceCryptoStatusResponse(BaseModel):
    """Public cryptographic readiness status for a registered device."""
    device_id: str = Field(..., examples=["DEVICE-001"])
    rescue_id: str = Field(..., examples=["RESQ-001"])
    is_initialized: bool = Field(..., examples=[True])
    signing_public_key: Optional[str] = Field(None, examples=["MCowBQYDK2VwAyEA..."])
    encryption_public_key: Optional[str] = Field(None, examples=["MC4CAQAwBQYDK2Vu..."])
    algorithms: Dict[str, str] = Field(
        default_factory=lambda: {
            "signature": "Ed25519",
            "key_agreement": "X25519",
            "kdf": "HKDF-SHA256",
            "authenticated_cipher": "ChaCha20-Poly1305",
        }
    )
