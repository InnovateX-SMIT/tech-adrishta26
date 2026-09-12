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
    is_online: bool = Field(True, examples=[True])
    is_available_for_relay: bool = Field(True, examples=[True])


class UpdateNodeStateRequest(BaseModel):
    """Request body for PATCH /api/mesh/nodes/{node_id}."""

    is_online: bool | None = Field(None, examples=[True])
    is_available_for_relay: bool | None = Field(None, examples=[True])


class RouteDiscoveryResponse(BaseModel):
    """Pure path discovery result without packet transmission."""

    source_device_id: str = Field(..., examples=["DEVICE-001"])
    destination_device_id: str = Field(..., examples=["DEVICE-004"])
    reachable: bool = Field(..., examples=[True])
    path: list[str] = Field(default_factory=list, examples=[["DEVICE-001", "DEVICE-002", "DEVICE-004"]])
    hop_count: int = Field(0, examples=[2])
    failure_reason: str | None = Field(None, examples=[None])


class TopologyResponse(BaseModel):
    """Full network topology returned by GET /api/mesh/topology."""

    nodes: list[NodeInfo]
    edges: list[tuple[str, str]]


class SendPacketRequest(BaseModel):
    """Request body for POST /api/mesh/send."""

    sender_id: str = Field(..., examples=["NODE-A"])
    receiver_id: str = Field(..., examples=["NODE-E"])
    payload: Any = Field(..., examples=["Hello, mesh!"])
    ttl: int = Field(10, ge=1, le=100, examples=[10])


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
    ttl: int = Field(10, examples=[10])
    hop_log: list[HopRecordSchema] = Field(default_factory=list)


class CapturedPacketsResponse(BaseModel):
    """Packets observed by an attacker node."""

    node_id: str = Field(..., examples=["ATTACKER"])
    captured: list[PacketResponse] = Field(default_factory=list)


class AddNodeRequest(BaseModel):
    """Request body for POST /api/mesh/nodes."""

    node_id: str = Field(..., min_length=1, examples=["DEVICE-001"])
    is_attacker: bool = Field(False, examples=[False])


class ConnectNodesRequest(BaseModel):
    """Request body for POST /api/mesh/connect and POST /api/mesh/disconnect."""

    node_a: str = Field(..., min_length=1, examples=["DEVICE-001"])
    node_b: str = Field(..., min_length=1, examples=["DEVICE-002"])


class DeliveryLogSchema(BaseModel):
    """Routing and delivery audit log entry."""

    packet_id: str = Field(..., examples=["pkt-001"])
    source: str = Field(..., examples=["DEVICE-001"])
    destination: str = Field(..., examples=["DEVICE-004"])
    route: list[str] = Field(default_factory=list, examples=[["DEVICE-001", "DEVICE-002", "DEVICE-004"]])
    hops: list[HopRecordSchema] = Field(default_factory=list)
    status: str = Field(..., examples=["delivered"])
    error: str | None = Field(None, examples=[None])
    timestamp: str = Field(..., examples=["2026-09-12T07:49:07.000000+00:00"])
