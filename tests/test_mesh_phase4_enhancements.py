"""
test_mesh_phase4_enhancements.py — Verification of Phase 4 prompt requirements:
- Online / offline node state handling
- Exclusion of offline nodes from routing
- Dynamic rerouting around offline relay nodes
- TTL decrementing and TTL expiration termination
- Pure route discovery endpoint (GET /api/mesh/routes/{source}/{destination})
- Node state update API (PATCH /api/mesh/nodes/{node_id})
- Self-link rejection
- Link alias endpoints (/links)
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.mesh_network import MeshNetwork, NoRouteError, TtlExpiredError
from backend.app.core.mesh_node import MeshNode
from backend.app.core.mesh_packet import MeshPacket
from backend.app.main import app
from backend.app.services.mesh_service import build_demo_network, get_network, reset_network

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_mesh():
    reset_network()
    yield
    reset_network()


def test_node_online_offline_toggle():
    node = MeshNode("NODE-1", is_online=True)
    assert node.is_online is True
    node.is_online = False
    assert node.is_online is False


def test_offline_node_excluded_from_routing():
    net = MeshNetwork()
    a = MeshNode("A")
    b = MeshNode("B", is_online=False)  # offline relay
    c = MeshNode("C")
    for n in (a, b, c):
        net.add_node(n)
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")

    with pytest.raises(NoRouteError) as exc_info:
        net.find_route("A", "C")
    assert "No route found" in str(exc_info.value)


def test_offline_relay_forces_reroute():
    # Topology:
    # A -- B -- D
    # |         |
    # +--- C ---+
    net = MeshNetwork()
    a = MeshNode("A")
    b = MeshNode("B")
    c = MeshNode("C")
    d = MeshNode("D")
    for n in (a, b, c, d):
        net.add_node(n)
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "D")
    net.connect_nodes("A", "C")
    net.connect_nodes("C", "D")

    # Initially route goes via B (alphabetical tie-breaker)
    route1 = net.find_route("A", "D")
    assert route1 == ["A", "B", "D"]

    # When B goes offline, route dynamically falls back to C
    b.is_online = False
    route2 = net.find_route("A", "D")
    assert route2 == ["A", "C", "D"]


def test_offline_source_fails_routing():
    net = MeshNetwork()
    a = MeshNode("A", is_online=False)
    b = MeshNode("B")
    net.add_node(a)
    net.add_node(b)
    net.connect_nodes("A", "B")

    with pytest.raises(NoRouteError) as exc_info:
        net.find_route("A", "B")
    assert "Source node 'A' is offline" in str(exc_info.value)


def test_offline_destination_fails_routing():
    net = MeshNetwork()
    a = MeshNode("A")
    b = MeshNode("B", is_online=False)
    net.add_node(a)
    net.add_node(b)
    net.connect_nodes("A", "B")

    with pytest.raises(NoRouteError) as exc_info:
        net.find_route("A", "B")
    assert "Destination node 'B' is offline" in str(exc_info.value)


def test_ttl_decrements_per_hop():
    net = MeshNetwork()
    a = MeshNode("A")
    b = MeshNode("B")
    c = MeshNode("C")
    for n in (a, b, c):
        net.add_node(n)
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")

    pkt = MeshPacket(packet_id="p1", sender_id="A", receiver_id="C", ttl=5)
    delivered = net.send_packet(pkt)
    assert delivered.status == "delivered"
    assert delivered.ttl == 3  # 5 - 2 hops = 3
    assert len(delivered.hop_log) == 2


def test_ttl_expiration_terminates_delivery():
    net = MeshNetwork()
    a = MeshNode("A")
    b = MeshNode("B")
    c = MeshNode("C")
    d = MeshNode("D")
    for n in (a, b, c, d):
        net.add_node(n)
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")
    net.connect_nodes("C", "D")

    # Route A->B->C->D requires 3 hops; setting TTL=2 must expire at hop 3
    pkt = MeshPacket(packet_id="p-exp", sender_id="A", receiver_id="D", ttl=2)
    with pytest.raises(TtlExpiredError) as exc_info:
        net.send_packet(pkt)
    assert "TTL expired" in str(exc_info.value)
    assert pkt.status == "expired"
    # Destination D must NOT have received it
    assert len(d.inbox) == 0


def test_self_link_rejected():
    net = MeshNetwork()
    a = MeshNode("A")
    net.add_node(a)
    with pytest.raises(ValueError) as exc_info:
        net.connect_nodes("A", "A")
    assert "Self-connections are not permitted" in str(exc_info.value)


def test_route_discovery_endpoint_success():
    build_demo_network()
    resp = client.get("/api/mesh/routes/NODE-A/NODE-E")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reachable"] is True
    assert data["source_device_id"] == "NODE-A"
    assert data["destination_device_id"] == "NODE-E"
    assert data["path"] == ["NODE-A", "NODE-B", "NODE-C", "NODE-E"]
    assert data["hop_count"] == 3


def test_route_discovery_endpoint_unreachable():
    client.post("/api/mesh/nodes", json={"node_id": "ISOLATED", "is_attacker": False})
    client.post("/api/mesh/nodes", json={"node_id": "TARGET", "is_attacker": False})
    resp = client.get("/api/mesh/routes/ISOLATED/TARGET")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reachable"] is False
    assert data["path"] == []
    assert data["hop_count"] == 0
    assert "No route found" in data["failure_reason"]


def test_patch_node_state_api():
    build_demo_network()
    # Toggle NODE-B offline
    resp = client.patch("/api/mesh/nodes/NODE-B", json={"is_online": False})
    assert resp.status_code == 200
    assert resp.json()["is_online"] is False

    # Route A -> E should now be unreachable because B is the bridge
    route_resp = client.get("/api/mesh/routes/NODE-A/NODE-E")
    assert route_resp.status_code == 200
    assert route_resp.json()["reachable"] is False

    # Toggle NODE-B back online
    resp2 = client.patch("/api/mesh/nodes/NODE-B", json={"is_online": True})
    assert resp2.status_code == 200
    assert resp2.json()["is_online"] is True

    # Route A -> E should now be reachable again
    route_resp2 = client.get("/api/mesh/routes/NODE-A/NODE-E")
    assert route_resp2.status_code == 200
    assert route_resp2.json()["reachable"] is True


def test_link_alias_endpoints():
    client.post("/api/mesh/nodes", json={"node_id": "N1"})
    client.post("/api/mesh/nodes", json={"node_id": "N2"})

    # Connect via POST /api/mesh/links
    resp_conn = client.post("/api/mesh/links", json={"node_a": "N1", "node_b": "N2"})
    assert resp_conn.status_code == 200

    topo = client.get("/api/mesh/topology").json()
    assert ["N1", "N2"] in topo["edges"]

    # Disconnect via DELETE /api/mesh/links/N1/N2
    resp_disc = client.delete("/api/mesh/links/N1/N2")
    assert resp_disc.status_code == 200

    topo2 = client.get("/api/mesh/topology").json()
    assert ["N1", "N2"] not in topo2["edges"]
