"""
mesh.py — FastAPI router for the Phase 4 mesh simulation endpoints.

All routes are mounted under /api/mesh (prefix set in routes/__init__.py).

Endpoints:
    POST   /mesh/demo              Reset and build the 5-node demo topology
    GET    /mesh/topology          Return current topology snapshot
    POST   /mesh/send              Send a packet and return traversal log
    GET    /mesh/node/{node_id}/inbox      Packets delivered to a node
    GET    /mesh/node/{node_id}/captured   Packets captured by an attacker node
    DELETE /mesh/reset             Clear the network (for testing / fresh demos)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.app.core.mesh_network import NoRouteError
from backend.app.core.mesh_packet import MeshPacket
from backend.app.models.schemas import (
    CapturedPacketsResponse,
    HopRecordSchema,
    NodeInfo,
    PacketResponse,
    SendPacketRequest,
    TopologyResponse,
)
from backend.app.services.mesh_service import (
    build_demo_network,
    get_network,
    reset_network,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _packet_to_response(packet: MeshPacket, status: str = "delivered") -> PacketResponse:
    """Convert a MeshPacket dataclass to a PacketResponse Pydantic model."""
    return PacketResponse(
        packet_id=packet.packet_id,
        sender_id=packet.sender_id,
        receiver_id=packet.receiver_id,
        payload=packet.payload,
        status=status,
        hop_log=[
            HopRecordSchema(
                hop_number=h.hop_number,
                from_node=h.from_node,
                to_node=h.to_node,
                timestamp=h.timestamp,
            )
            for h in packet.hop_log
        ],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/demo",
    summary="Build demo network",
    description=(
        "Reset the shared mesh network and construct the standard 5-node Phase 4 "
        "demo topology (NODE-A through NODE-E plus one passive ATTACKER node)."
    ),
)
async def build_demo() -> dict:
    net = build_demo_network()
    topo = net.get_topology()
    return {
        "message": "Demo network built successfully.",
        "node_count": len(topo["nodes"]),
        "edge_count": len(topo["edges"]),
    }


@router.get(
    "/topology",
    response_model=TopologyResponse,
    summary="Get current topology",
    description="Return a snapshot of all registered nodes and edges.",
)
async def get_topology() -> TopologyResponse:
    net = get_network()
    topo = net.get_topology()
    return TopologyResponse(
        nodes=[
            NodeInfo(
                node_id=n["node_id"],
                neighbors=n["neighbors"],
                is_attacker=n["is_attacker"],
            )
            for n in topo["nodes"]
        ],
        edges=[tuple(e) for e in topo["edges"]],  # type: ignore[misc]
    )


@router.post(
    "/send",
    response_model=PacketResponse,
    summary="Send a packet",
    description=(
        "Route a packet from sender to receiver across the mesh.  "
        "Returns the full traversal log.  Raises 404 if either node is unknown "
        "and 422 if no route exists between the two nodes."
    ),
)
async def send_packet(body: SendPacketRequest) -> PacketResponse:
    net = get_network()

    if body.sender_id not in net.nodes:
        raise HTTPException(
            status_code=404,
            detail=f"Sender node {body.sender_id!r} not found in the mesh.",
        )
    if body.receiver_id not in net.nodes:
        raise HTTPException(
            status_code=404,
            detail=f"Receiver node {body.receiver_id!r} not found in the mesh.",
        )

    packet = MeshPacket(
        packet_id=str(uuid.uuid4()),
        sender_id=body.sender_id,
        receiver_id=body.receiver_id,
        payload=body.payload,
    )

    try:
        net.send_packet(packet)
    except NoRouteError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _packet_to_response(packet, status="delivered")


@router.get(
    "/node/{node_id}/inbox",
    response_model=list[PacketResponse],
    summary="Node inbox",
    description="Return all packets delivered to the specified node.",
)
async def get_inbox(node_id: str) -> list[PacketResponse]:
    net = get_network()
    if node_id not in net.nodes:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found.")
    node = net.nodes[node_id]
    return [_packet_to_response(p) for p in node.inbox]


@router.get(
    "/node/{node_id}/captured",
    response_model=CapturedPacketsResponse,
    summary="Attacker captured packets",
    description=(
        "Return packets captured (sniffed) by the specified attacker node.  "
        "Returns an empty list for non-attacker nodes — they simply have no "
        "captured packets."
    ),
)
async def get_captured(node_id: str) -> CapturedPacketsResponse:
    net = get_network()
    if node_id not in net.nodes:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found.")
    node = net.nodes[node_id]
    return CapturedPacketsResponse(
        node_id=node_id,
        captured=[_packet_to_response(p, status="captured") for p in node.captured_packets],
    )


@router.delete(
    "/reset",
    summary="Reset the mesh network",
    description="Clear all nodes and edges from the shared network instance.",
)
async def reset() -> dict:
    reset_network()
    return {"message": "Mesh network has been reset."}
