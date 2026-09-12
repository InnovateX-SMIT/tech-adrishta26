"""
test_mesh_phase4_audit.py — Verification tests for Phase 4 requirements.

Tests all 8 explicit specification requirements:
1. Direct delivery (A -- B)
2. Multi-hop delivery (A -- B -- C -- D)
3. Alternative route selection upon topological shift
4. Unreachable destination handling and failure logging
5. Strict payload preservation across multiple hops (opaque data)
6. Loop prevention and termination on cyclic graphs
7. Disconnection and dynamic re-routing
8. Unique packet IDs and duplicate suppression
"""

from fastapi.testclient import TestClient
import pytest

from backend.app.core.mesh_network import MeshNetwork, NoRouteError
from backend.app.core.mesh_node import MeshNode
from backend.app.core.mesh_packet import MeshPacket
from backend.app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 — Direct delivery
# ---------------------------------------------------------------------------

def test_direct_delivery():
    net = MeshNetwork()
    n1 = MeshNode(device_id="DEVICE-001")
    n2 = MeshNode(device_id="DEVICE-002")
    net.add_node(n1)
    net.add_node(n2)
    net.connect_nodes("DEVICE-001", "DEVICE-002")

    pkt = MeshPacket(
        packet_id="PKT-001",
        source="DEVICE-001",
        destination="DEVICE-002",
        payload="Medic dispatched to Sector 1",
    )
    net.send_packet(pkt)

    assert len(n2.inbox) == 1
    assert n2.inbox[0].packet_id == "PKT-001"
    assert n2.inbox[0].payload == "Medic dispatched to Sector 1"
    assert len(pkt.hop_log) == 1
    assert pkt.hop_log[0].from_node == "DEVICE-001"
    assert pkt.hop_log[0].to_node == "DEVICE-002"


# ---------------------------------------------------------------------------
# Test 2 — Multi-hop delivery
# ---------------------------------------------------------------------------

def test_multihop_delivery():
    net = MeshNetwork()
    for i in range(1, 5):
        net.add_node(MeshNode(f"DEVICE-00{i}"))
    net.connect_nodes("DEVICE-001", "DEVICE-002")
    net.connect_nodes("DEVICE-002", "DEVICE-003")
    net.connect_nodes("DEVICE-003", "DEVICE-004")

    pkt = MeshPacket(
        packet_id="PKT-002",
        source="DEVICE-001",
        destination="DEVICE-004",
        payload={"alert": "Power outage in Zone 4", "priority": "CRITICAL"},
    )
    net.send_packet(pkt)

    dest_node = net.nodes["DEVICE-004"]
    assert len(dest_node.inbox) == 1
    assert dest_node.inbox[0].payload == {"alert": "Power outage in Zone 4", "priority": "CRITICAL"}

    route_hops = [(h.from_node, h.to_node) for h in pkt.hop_log]
    assert route_hops == [
        ("DEVICE-001", "DEVICE-002"),
        ("DEVICE-002", "DEVICE-003"),
        ("DEVICE-003", "DEVICE-004"),
    ]


# ---------------------------------------------------------------------------
# Test 3 — Alternative route
# ---------------------------------------------------------------------------

def test_alternative_route():
    net = MeshNetwork()
    # Diamond topology:
    # DEVICE-001 --- DEVICE-002 --- DEVICE-004
    #       \                        /
    #        ------- DEVICE-003 ----
    for did in ["DEVICE-001", "DEVICE-002", "DEVICE-003", "DEVICE-004"]:
        net.add_node(MeshNode(did))

    net.connect_nodes("DEVICE-001", "DEVICE-002")
    net.connect_nodes("DEVICE-002", "DEVICE-004")
    net.connect_nodes("DEVICE-001", "DEVICE-003")
    net.connect_nodes("DEVICE-003", "DEVICE-004")

    route = net.find_route("DEVICE-001", "DEVICE-004")
    assert len(route) == 3
    assert route[0] == "DEVICE-001"
    assert route[-1] == "DEVICE-004"


# ---------------------------------------------------------------------------
# Test 4 — Unreachable node & failed delivery logging
# ---------------------------------------------------------------------------

def test_unreachable_node_and_failed_delivery_logged():
    net = MeshNetwork()
    # Island 1
    net.add_node(MeshNode("DEVICE-001"))
    net.add_node(MeshNode("DEVICE-002"))
    net.connect_nodes("DEVICE-001", "DEVICE-002")

    # Island 2 (disconnected)
    net.add_node(MeshNode("DEVICE-003"))
    net.add_node(MeshNode("DEVICE-004"))
    net.connect_nodes("DEVICE-003", "DEVICE-004")

    pkt = MeshPacket(
        packet_id="PKT-FAIL",
        source="DEVICE-001",
        destination="DEVICE-004",
        payload="SOS message",
    )

    with pytest.raises(NoRouteError) as exc_info:
        net.send_packet(pkt)

    assert "No route found" in str(exc_info.value)

    # Verify failure is recorded in network logs
    logs = net.get_delivery_logs()
    assert len(logs) == 1
    assert logs[0].packet_id == "PKT-FAIL"
    assert logs[0].source == "DEVICE-001"
    assert logs[0].destination == "DEVICE-004"
    assert logs[0].status == "failed"
    assert "No route found" in (logs[0].error or "")


# ---------------------------------------------------------------------------
# Test 5 — Payload preservation (opaque data)
# ---------------------------------------------------------------------------

def test_payload_preservation_complex_types():
    net = MeshNetwork()
    for i in range(1, 4):
        net.add_node(MeshNode(f"DEVICE-00{i}"))
    net.connect_nodes("DEVICE-001", "DEVICE-002")
    net.connect_nodes("DEVICE-002", "DEVICE-003")

    complex_payload = {
        "nested": {"key": [1, 2, 3], "flag": True},
        "binary_like_string": "0a5XCWErpI5UTmyj4zApjV0XEw41mI39MuNnZzQUEuk=",
        "count": 42,
        "null_val": None,
    }

    pkt = MeshPacket(
        packet_id="PKT-OPAQUE",
        source="DEVICE-001",
        destination="DEVICE-003",
        payload=complex_payload,
    )
    net.send_packet(pkt)

    dest = net.nodes["DEVICE-003"]
    assert len(dest.inbox) == 1
    assert dest.inbox[0].payload == complex_payload
    # Ensure deep structural identity
    assert dest.inbox[0].payload["nested"]["key"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# Test 6 — Loop prevention
# ---------------------------------------------------------------------------

def test_complex_cyclic_graph_loop_prevention():
    net = MeshNetwork()
    # Complex cycle with cross links:
    # A - B - C - D - E - A
    # |       |
    # D - - - B
    nodes = ["N1", "N2", "N3", "N4", "N5"]
    for nid in nodes:
        net.add_node(MeshNode(nid))
    net.connect_nodes("N1", "N2")
    net.connect_nodes("N2", "N3")
    net.connect_nodes("N3", "N4")
    net.connect_nodes("N4", "N5")
    net.connect_nodes("N5", "N1")
    net.connect_nodes("N1", "N4")
    net.connect_nodes("N2", "N4")

    # Routing terminates and finds shortest path (N1 -> N4 is 1 hop direct)
    route = net.find_route("N1", "N4")
    assert route == ["N1", "N4"]

    route_to_n3 = net.find_route("N1", "N3")
    assert len(route_to_n3) == 3  # N1 -> N2 -> N3 or N1 -> N4 -> N3


# ---------------------------------------------------------------------------
# Test 7 — Disconnection and node removal
# ---------------------------------------------------------------------------

def test_disconnection_and_rerouting():
    net = MeshNetwork()
    for nid in ["A", "B", "C", "D"]:
        net.add_node(MeshNode(nid))

    net.connect_nodes("A", "B")
    net.connect_nodes("B", "D")
    net.connect_nodes("A", "C")
    net.connect_nodes("C", "D")

    assert net.has_connection("A", "B") is True
    assert net.has_connection("A", "D") is False

    # Disconnect B-D
    net.disconnect_nodes("B", "D")
    assert net.has_connection("B", "D") is False

    # Route must now go through C
    route = net.find_route("A", "D")
    assert route == ["A", "C", "D"]

    # Remove node C
    net.remove_node("C")
    assert "C" not in net.nodes
    assert "C" not in net.nodes["A"].neighbors
    assert "C" not in net.nodes["D"].neighbors

    # Now A -> D should fail
    with pytest.raises(NoRouteError):
        net.find_route("A", "D")


# ---------------------------------------------------------------------------
# Test 8 — Duplicate packet suppression
# ---------------------------------------------------------------------------

def test_duplicate_packet_suppression():
    node = MeshNode("DEVICE-RECV")
    pkt = MeshPacket(packet_id="PKT-DUP-01", source="A", destination="DEVICE-RECV", payload="msg")

    # First receipt: accepted
    assert node.receive_packet(pkt) is True
    assert len(node.inbox) == 1

    # Duplicate receipt with same packet_id: suppressed
    assert node.receive_packet(pkt) is False
    assert len(node.inbox) == 1


# ---------------------------------------------------------------------------
# Test 9 — API Integration for new Phase 4 endpoints
# ---------------------------------------------------------------------------

def test_mesh_api_nodes_and_logs():
    client.delete("/api/mesh/reset")

    # Add node via API
    resp = client.post("/api/mesh/nodes", json={"node_id": "DEVICE-001"})
    assert resp.status_code == 201
    assert resp.json()["node_id"] == "DEVICE-001"

    # Add duplicate node returns 409
    dup_resp = client.post("/api/mesh/nodes", json={"node_id": "DEVICE-001"})
    assert dup_resp.status_code == 409

    # Add second node
    client.post("/api/mesh/nodes", json={"node_id": "DEVICE-002"})

    # Connect nodes via API
    conn_resp = client.post(
        "/api/mesh/connect",
        json={"node_a": "DEVICE-001", "node_b": "DEVICE-002"},
    )
    assert conn_resp.status_code == 200

    # List nodes
    nodes_resp = client.get("/api/mesh/nodes")
    assert nodes_resp.status_code == 200
    assert len(nodes_resp.json()) == 2

    # Send packet
    send_resp = client.post(
        "/api/mesh/send",
        json={
            "sender_id": "DEVICE-001",
            "receiver_id": "DEVICE-002",
            "payload": "Triage report",
        },
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] == "delivered"

    # Query delivery logs
    logs_resp = client.get("/api/mesh/logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) == 1
    assert logs[0]["source"] == "DEVICE-001"
    assert logs[0]["destination"] == "DEVICE-002"
    assert logs[0]["status"] == "delivered"

    # Disconnect nodes via API
    disc_resp = client.post(
        "/api/mesh/disconnect",
        json={"node_a": "DEVICE-001", "node_b": "DEVICE-002"},
    )
    assert disc_resp.status_code == 200

    # Sending now fails with 422 (unreachable)
    fail_send = client.post(
        "/api/mesh/send",
        json={
            "sender_id": "DEVICE-001",
            "receiver_id": "DEVICE-002",
            "payload": "Should fail",
        },
    )
    assert fail_send.status_code == 422

    # Logs now reflect the failure
    logs_after = client.get("/api/mesh/logs").json()
    assert len(logs_after) == 2
    assert logs_after[1]["status"] == "failed"
