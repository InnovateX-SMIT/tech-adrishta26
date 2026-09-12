from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class SimulationMode(str, Enum):
    VULNERABLE = "vulnerable"
    PROTECTED = "protected"


class CapturedPacket(BaseModel):
    simulation_id: str = Field(..., description="Unique simulation execution identifier")
    capture_id: str = Field(..., description="Unique capture identifier (e.g. CAP-xxxx)")
    packet_id: str = Field(..., description="Captured mesh packet identifier")
    message_id: str = Field(..., description="Transmitted message identifier")
    captured_at: str = Field(..., description="ISO 8601 UTC timestamp of interception")
    captured_at_node: str = Field(..., description="Node ID where the packet was sniffed/intercepted")
    sender_id: str = Field(..., description="Sender rescue or device ID")
    recipient_id: str = Field(..., description="Recipient rescue or device ID")
    route: List[str] = Field(default_factory=list, description="Ordered list of nodes in route")
    communication_mode: str = Field(..., description="'vulnerable' or 'protected'")
    packet_size: int = Field(..., description="Serialized payload byte size")
    metadata_visible_to_attacker: bool = Field(
        default=True,
        description="Routing metadata (IDs, route, timestamp) visible to network observers",
    )
    contains_plaintext: bool = Field(
        ...,
        description="True if original message is contained in the captured payload",
    )
    plaintext_exposed: bool = Field(
        ...,
        description="True if original plaintext is readable by the sniffing attacker",
    )
    ciphertext_present: bool = Field(..., description="True if AEAD ciphertext is present")
    signature_present: bool = Field(..., description="True if digital signature is present")
    sniffed_content: str = Field(
        ...,
        description="Observed payload content (unencrypted plaintext in vulnerable mode; ciphertext preview in protected mode)",
    )
    message_readable_by_attacker: bool = Field(
        ...,
        description="True if attacker can read the original emergency message",
    )
    security_result: str = Field(
        ...,
        description="'Message exposed' or 'Plaintext protected'",
    )
    explanation: str = Field(
        ...,
        description="Plain-English human explanation of the capture result",
    )
    raw_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Captured wire payload representation",
    )

    @model_validator(mode="after")
    def validate_protected_confidentiality(self) -> "CapturedPacket":
        """Strict validation: protected packets must never contain or expose plaintext."""
        if self.communication_mode == "protected":
            if self.contains_plaintext or self.plaintext_exposed or self.message_readable_by_attacker:
                raise ValueError("Protected mode packets must never contain or expose plaintext.")
            if "plaintext" in (self.raw_payload or {}):
                raise ValueError("Protected wire payload must not contain a 'plaintext' field.")
        return self


class SimulateAttackRequest(BaseModel):
    mode: SimulationMode = Field(
        default=SimulationMode.PROTECTED,
        description="Simulation mode: 'vulnerable' or 'protected'",
    )
    sender_id: str = Field(..., description="Sender Rescue ID (e.g. 'RESQ-001')")
    recipient_id: str = Field(..., description="Recipient Rescue ID (e.g. 'RESQ-002')")
    message: str = Field(
        default="SOS: Three people are trapped in Building B.",
        description="Emergency distress message text",
    )
    attacker_node_id: Optional[str] = Field(
        default=None,
        description="Optional node ID where attacker listens (defaults to active sniffer node)",
    )


class SimulateAttackResponse(BaseModel):
    simulation_id: str
    mode: str
    packet_id: str
    message_id: str
    captured: bool
    captured_packet: Optional[CapturedPacket] = None
    route: List[str]
    receiver_result: Dict[str, Any]
    security_logs: List[str]
    summary_sentence: str


class TamperCaptureRequest(BaseModel):
    capture_id: str = Field(..., description="Capture identifier to mutate")
    tamper_field: str = Field(
        default="ciphertext",
        description="Field to tamper: 'ciphertext', 'signature', or 'nonce'",
    )
    recipient_id: Optional[str] = Field(
        default=None,
        description="Recipient device to submit tampered packet to",
    )


class TamperCaptureResponse(BaseModel):
    capture_id: str
    tampered_field: str
    receiver_status: str
    rejection_reason: Optional[str] = None
    rejection_detail: Optional[str] = None
    plaintext_revealed: bool = False
    explanation: str


class AttackStatusResponse(BaseModel):
    total_captures: int
    vulnerable_captures: int
    protected_captures: int
    last_capture: Optional[CapturedPacket] = None
