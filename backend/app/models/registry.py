from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemberStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class RescueMember(BaseModel):
    rescue_id: str = Field(..., examples=["RESQ-001"])
    name: str = Field(..., examples=["Aarav Sharma"])
    team: str = Field(..., examples=["Rescue Unit A"])
    role: str = Field(..., examples=["Field Responder"])
    device_id: str = Field(..., examples=["DEVICE-001"])
    signing_public_key: Optional[str] = Field(None, examples=[None])
    encryption_public_key: Optional[str] = Field(None, examples=[None])
    status: MemberStatus = Field(MemberStatus.ACTIVE, examples=[MemberStatus.ACTIVE])
    created_at: str = Field(..., examples=["2026-09-12T10:00:00Z"])
    revoked_at: Optional[str] = Field(None, examples=[None])

    @model_validator(mode="after")
    def verify_no_private_keys(self) -> "RescueMember":
        for key in self.__dict__.keys():
            lower = key.lower()
            if "private" in lower or "secret" in lower or "mnemonic" in lower or "seed" in lower:
                raise ValueError("Registry records cannot contain private key or secret material.")
        return self


class RegisterMemberRequest(BaseModel):
    # Strict Phase 2 rule: forbid extra fields (e.g. private_key, secret_key, signing_public_key)
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, examples=["Aarav Sharma"])
    team: str = Field(..., min_length=1, examples=["Rescue Unit A"])
    role: str = Field(..., min_length=1, examples=["Field Responder"])

    @field_validator("name", "team", "role")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or whitespace-only.")
        return trimmed


class MemberStatusResponse(BaseModel):
    rescue_id: str = Field(..., examples=["RESQ-001"])
    status: MemberStatus = Field(..., examples=[MemberStatus.ACTIVE])
    is_active: bool = Field(..., examples=[True])


class RegistryMembersResponse(BaseModel):
    version: int = Field(1, examples=[1])
    total: int = Field(..., examples=[1])
    active_count: int = Field(..., examples=[1])
    revoked_count: int = Field(..., examples=[0])
    members: List[RescueMember]
