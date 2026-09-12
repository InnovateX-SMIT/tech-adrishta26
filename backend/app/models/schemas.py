from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["RESQ backend"])
    phase: str = Field(..., examples=["phase-4"])


class SystemInfoResponse(BaseModel):
    project: str = Field(..., examples=["RESQ"])
    mode: str = Field(..., examples=["development"])
    mesh_enabled: bool = Field(False, examples=[True])
    encryption_enabled: bool = Field(False, examples=[False])
    phase: int = Field(4, examples=[4])


# ---------------------------------------------------------------------------
# Phase 4 — Mesh API schemas
# ---------------------------------------------------------------------------


class NodeInfo(BaseModel):
    """Serialisable snapshot of a single mesh node."""

    node_id: str = Field(..., examples=["NODE-A"])
    neighbors: list[str] = Field(default_factory=list, examples=[["NODE-B"]])
    is_attacker: bool = Field(False, examples=[False])


class TopologyResponse(BaseModel):
    """Full network topology returned by GET /api/mesh/topology."""

    nodes: list[NodeInfo]
    edges: list[tuple[str, str]]


class SendPacketRequest(BaseModel):
    """Request body for POST /api/mesh/send."""

    sender_id: str = Field(..., examples=["NODE-A"])
    receiver_id: str = Field(..., examples=["NODE-E"])
    payload: Any = Field(..., examples=["Hello, mesh!"])


class HopRecordSchema(BaseModel):
    """Single traversal record appended to a packet at each hop."""

    hop_number: int = Field(..., examples=[1])
    from_node: str = Field(..., examples=["NODE-A"])
    to_node: str = Field(..., examples=["NODE-B"])
    timestamp: str = Field(..., examples=["2026-09-12T07:49:07.000000+00:00"])


class PacketResponse(BaseModel):
    """Full packet record returned after a send or from an inbox query."""

    packet_id: str = Field(..., examples=["pkt-001"])
    sender_id: str = Field(..., examples=["NODE-A"])
    receiver_id: str = Field(..., examples=["NODE-E"])
    payload: Any = Field(..., examples=["Hello, mesh!"])
    status: str = Field(..., examples=["delivered"])
    hop_log: list[HopRecordSchema] = Field(default_factory=list)


class CapturedPacketsResponse(BaseModel):
    """Packets observed by an attacker node."""

    node_id: str = Field(..., examples=["ATTACKER"])
    captured: list[PacketResponse] = Field(default_factory=list)
