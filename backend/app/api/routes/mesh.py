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
from backend.app.core.mesh_node import MeshNode
from backend.app.core.mesh_packet import MeshPacket
from backend.app.models.schemas import (
    AddNodeRequest,
    CapturedPacketsResponse,
    ConnectNodesRequest,
    DeliveryLogSchema,
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
        "demo topology (supports either NODE-A..E or Phase 2 DEVICE-001..005)."
    ),
)
async def build_demo(use_device_ids: bool = False) -> dict:
    net = build_demo_network(use_device_ids=use_device_ids)
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


@router.get(
    "/nodes",
    response_model=list[NodeInfo],
    summary="List all nodes",
    description="Return a list of all currently registered nodes in the mesh.",
)
async def list_nodes() -> list[NodeInfo]:
    net = get_network()
    return [
        NodeInfo(
            node_id=n.node_id,
            neighbors=sorted(n.neighbors),
            is_attacker=n.is_attacker,
        )
        for n in net.nodes.values()
    ]


@router.post(
    "/nodes",
    response_model=NodeInfo,
    status_code=201,
    summary="Register a new node",
    description="Add a simulated rescue node to the mesh network.",
)
async def add_node(body: AddNodeRequest) -> NodeInfo:
    net = get_network()
    if body.node_id in net.nodes:
        raise HTTPException(
            status_code=409,
            detail=f"Node {body.node_id!r} is already registered in the mesh.",
        )
    node = MeshNode(node_id=body.node_id, is_attacker=body.is_attacker)
    net.add_node(node)
    return NodeInfo(
        node_id=node.node_id,
        neighbors=sorted(node.neighbors),
        is_attacker=node.is_attacker,
    )


@router.delete(
    "/nodes/{node_id}",
    summary="Remove a node",
    description="Remove a node from the mesh and cleanly disconnect all its edges.",
)
async def remove_node(node_id: str) -> dict:
    net = get_network()
    try:
        net.remove_node(node_id)
        return {"message": f"Node {node_id!r} removed successfully."}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/connect",
    summary="Connect two nodes",
    description="Create a bidirectional edge between two registered nodes.",
)
async def connect_nodes(body: ConnectNodesRequest) -> dict:
    net = get_network()
    try:
        net.connect_nodes(body.node_a, body.node_b)
        return {
            "message": f"Connected {body.node_a!r} and {body.node_b!r} successfully.",
            "edge": sorted([body.node_a, body.node_b]),
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot connect nodes: {exc}",
        ) from exc


@router.post(
    "/disconnect",
    summary="Disconnect two nodes",
    description="Remove the bidirectional edge between two registered nodes.",
)
async def disconnect_nodes(body: ConnectNodesRequest) -> dict:
    net = get_network()
    try:
        net.disconnect_nodes(body.node_a, body.node_b)
        return {
            "message": f"Disconnected {body.node_a!r} and {body.node_b!r} successfully.",
            "edge": sorted([body.node_a, body.node_b]),
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot disconnect nodes: {exc}",
        ) from exc


@router.get(
    "/logs",
    response_model=list[DeliveryLogSchema],
    summary="Delivery & routing logs",
    description="Return the ordered audit trail of all packet delivery attempts across the mesh.",
)
async def get_logs() -> list[DeliveryLogSchema]:
    net = get_network()
    return [
        DeliveryLogSchema(
            packet_id=log.packet_id,
            source=log.source,
            destination=log.destination,
            route=log.route,
            hops=[
                HopRecordSchema(
                    hop_number=h.hop_number,
                    from_node=h.from_node,
                    to_node=h.to_node,
                    timestamp=h.timestamp,
                )
                for h in log.hops
            ],
            status=log.status,
            error=log.error,
            timestamp=log.timestamp,
        )
        for log in net.get_delivery_logs()
    ]
