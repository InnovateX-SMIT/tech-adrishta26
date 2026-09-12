from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OperationalStatusPills(BaseModel):
    cellular_network: str = Field(
        default="OFFLINE (Blackout Active)",
        description="Status of traditional cellular/cloud connectivity",
    )
    cellular_status: str = Field(default="offline", description="'offline' or 'online'")
    emergency_mesh: str = Field(
        default="ACTIVE",
        description="Status of the ad-hoc peer-to-peer mesh network",
    )
    mesh_status: str = Field(default="active", description="'active' or 'degraded'")
    encryption: str = Field(
        default="ACTIVE (ChaCha20-Poly1305)",
        description="Zero-trust cryptographic payload encryption status",
    )
    encryption_status: str = Field(default="active", description="'active' or 'disabled'")
    identity_authority: str = Field(
        default="VERIFIED (Ed25519)",
        description="Sender authenticity and non-repudiation status",
    )
    identity_status: str = Field(default="verified", description="'verified' or 'unverified'")
    controlled_decryption: str = Field(
        default="ENFORCED",
        description="Status of Phase 6 authorization & controlled decryption gate",
    )
    decryption_status: str = Field(default="enforced", description="'enforced' or 'open'")


class DashboardNodeSummary(BaseModel):
    node_id: str
    device_id: str
    name: str
    team: str
    role: str
    is_online: bool
    is_attacker: bool
    is_keyed: bool
    neighbors: List[str]


class DashboardRouteSummary(BaseModel):
    route_id: str
    source: str
    destination: str
    hops: List[str]
    hop_count: int
    status: str


class DashboardMessagingSummary(BaseModel):
    total_messages: int
    delivered_count: int
    in_transit_count: int
    failed_count: int
    recent_messages: List[Dict[str, Any]]


class DashboardAttackerSummary(BaseModel):
    attacker_node_id: str
    is_sniffing: bool
    total_intercepted: int
    vulnerable_captures: int
    protected_captures: int
    latest_capture: Optional[Dict[str, Any]] = None
    readability_verdict: str


class DashboardSecuritySummary(BaseModel):
    active_responders_count: int
    keyed_devices_count: int
    revoked_count: int
    gate_success_rate: float
    recent_security_events: List[str]


class DashboardOverviewResponse(BaseModel):
    timestamp: str
    phase: int = 8
    phase_name: str = "phase-8"
    blackout_in_effect: bool = True
    operational_status: OperationalStatusPills
    nodes: List[DashboardNodeSummary]
    edges: List[List[str]]
    active_route: Optional[DashboardRouteSummary] = None
    messaging: DashboardMessagingSummary
    security: DashboardSecuritySummary
    attacker: DashboardAttackerSummary
    summary_takeaway: str = Field(
        default="The goal is not to prevent packet capture. The goal is to ensure that capturing a packet does not reveal the emergency message."
    )


class QuickDispatchRequest(BaseModel):
    mode: str = Field(default="protected", description="'protected' or 'vulnerable'")
    sender_id: str = Field(default="RESQ-001", description="Sender Rescue ID")
    recipient_id: str = Field(default="RESQ-002", description="Recipient Rescue ID")
    message: str = Field(
        default="SOS: Three people trapped in Building B. Air supply 20 min.",
        description="Emergency distress message text",
    )


class QuickDispatchResponse(BaseModel):
    status: str
    mode: str
    packet_id: str
    message_id: str
    route: List[str]
    hop_count: int
    captured_by_attacker: bool
    attacker_readable: bool
    attacker_sniffed: str
    security_gate_decision: str
    decrypted_message: Optional[str] = None
    explanation: str
    overview: DashboardOverviewResponse
