"""
test_mesh_api.py — Integration tests for the Phase 4 mesh API endpoints.

Each test that relies on mesh state calls DELETE /api/mesh/reset first
to ensure a clean slate, then POST /api/mesh/demo to build the standard
5-node topology.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def reset_and_build_demo() -> None:
    client.delete("/api/mesh/reset")
    r = client.post("/api/mesh/demo")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/mesh/demo
# ---------------------------------------------------------------------------


def test_demo_endpoint_builds_network():
    r = client.post("/api/mesh/demo")
    assert r.status_code == 200
    data = r.json()
    assert "node_count" in data
    assert data["node_count"] >= 5


def test_demo_endpoint_is_idempotent():
    """Calling demo twice should not error and should produce a consistent topology."""
    r1 = client.post("/api/mesh/demo")
    r2 = client.post("/api/mesh/demo")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["node_count"] == r2.json()["node_count"]


# ---------------------------------------------------------------------------
# GET /api/mesh/topology
# ---------------------------------------------------------------------------


def test_topology_returns_nodes_and_edges():
    reset_and_build_demo()
    r = client.get("/api/mesh/topology")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 5


def test_topology_includes_attacker_node():
    reset_and_build_demo()
    r = client.get("/api/mesh/topology")
    data = r.json()
    attackers = [n for n in data["nodes"] if n["is_attacker"]]
    assert len(attackers) >= 1


def test_topology_node_has_required_fields():
    reset_and_build_demo()
    r = client.get("/api/mesh/topology")
    node = r.json()["nodes"][0]
    assert "node_id" in node
    assert "neighbors" in node
    assert "is_attacker" in node


def test_topology_empty_after_reset():
    client.delete("/api/mesh/reset")
    r = client.get("/api/mesh/topology")
    assert r.status_code == 200
    data = r.json()
    assert data["nodes"] == []
    assert data["edges"] == []


# ---------------------------------------------------------------------------
# POST /api/mesh/send
# ---------------------------------------------------------------------------


def test_send_packet_returns_packet_response():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-E", "payload": "hello"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["sender_id"] == "NODE-A"
    assert data["receiver_id"] == "NODE-E"
    assert data["payload"] == "hello"
    assert data["status"] == "delivered"


def test_send_packet_has_hop_log():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-E", "payload": "trace-me"},
    )
    data = r.json()
    assert len(data["hop_log"]) >= 1
    first_hop = data["hop_log"][0]
    assert "hop_number" in first_hop
    assert "from_node" in first_hop
    assert "to_node" in first_hop
    assert "timestamp" in first_hop


def test_send_packet_first_hop_starts_at_sender():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-C", "payload": "check-start"},
    )
    data = r.json()
    assert data["hop_log"][0]["from_node"] == "NODE-A"


def test_send_packet_last_hop_ends_at_receiver():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-E", "payload": "check-end"},
    )
    data = r.json()
    assert data["hop_log"][-1]["to_node"] == "NODE-E"


def test_send_packet_unknown_sender_returns_404():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "GHOST", "receiver_id": "NODE-B", "payload": "x"},
    )
    assert r.status_code == 404


def test_send_packet_unknown_receiver_returns_404():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NOWHERE", "payload": "x"},
    )
    assert r.status_code == 404


def test_send_packet_no_route_returns_422():
    """Two isolated nodes produce a 422 when there is no route."""
    client.delete("/api/mesh/reset")

    from backend.app.services.mesh_service import get_network
    from backend.app.core.mesh_node import MeshNode

    net = get_network()
    net.add_node(MeshNode("ISLAND-A"))
    net.add_node(MeshNode("ISLAND-B"))
    # No edge between them

    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "ISLAND-A", "receiver_id": "ISLAND-B", "payload": "lost"},
    )
    assert r.status_code == 422


def test_send_accepts_non_string_payload():
    reset_and_build_demo()
    r = client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-B", "payload": {"key": "value"}},
    )
    assert r.status_code == 200
    assert r.json()["payload"] == {"key": "value"}


# ---------------------------------------------------------------------------
# GET /api/mesh/node/{node_id}/inbox
# ---------------------------------------------------------------------------


def test_inbox_is_empty_before_send():
    reset_and_build_demo()
    r = client.get("/api/mesh/node/NODE-E/inbox")
    assert r.status_code == 200
    assert r.json() == []


def test_inbox_contains_delivered_packet():
    reset_and_build_demo()
    client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-E", "payload": "inbox-test"},
    )
    r = client.get("/api/mesh/node/NODE-E/inbox")
    assert r.status_code == 200
    inbox = r.json()
    assert len(inbox) == 1
    assert inbox[0]["payload"] == "inbox-test"


def test_inbox_unknown_node_returns_404():
    reset_and_build_demo()
    r = client.get("/api/mesh/node/DOES-NOT-EXIST/inbox")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/mesh/node/{node_id}/captured
# ---------------------------------------------------------------------------


def test_captured_empty_before_send():
    reset_and_build_demo()
    r = client.get("/api/mesh/node/ATTACKER/captured")
    assert r.status_code == 200
    data = r.json()
    assert data["node_id"] == "ATTACKER"
    assert data["captured"] == []


def test_attacker_captures_traffic_through_adjacent_edge():
    reset_and_build_demo()
    # NODE-A → NODE-B → NODE-C → NODE-E passes through edges adjacent to ATTACKER
    client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-E", "payload": "sniff-me"},
    )
    r = client.get("/api/mesh/node/ATTACKER/captured")
    data = r.json()
    assert len(data["captured"]) >= 1
    payloads = [p["payload"] for p in data["captured"]]
    assert "sniff-me" in payloads


def test_captured_non_attacker_returns_empty():
    reset_and_build_demo()
    client.post(
        "/api/mesh/send",
        json={"sender_id": "NODE-A", "receiver_id": "NODE-E", "payload": "pass-through"},
    )
    r = client.get("/api/mesh/node/NODE-A/captured")
    data = r.json()
    # NODE-A is not an attacker — captured list is always empty
    assert data["captured"] == []


def test_captured_unknown_node_returns_404():
    reset_and_build_demo()
    r = client.get("/api/mesh/node/PHANTOM/captured")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/mesh/reset
# ---------------------------------------------------------------------------


def test_reset_empties_network():
    client.post("/api/mesh/demo")
    r = client.delete("/api/mesh/reset")
    assert r.status_code == 200
    topo = client.get("/api/mesh/topology").json()
    assert topo["nodes"] == []
