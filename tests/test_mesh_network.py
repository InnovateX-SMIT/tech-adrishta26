"""
test_mesh_network.py — Unit tests for MeshNetwork.

Covers all 8 required test scenarios:
1.  Node creation (≥3 nodes)
2.  Node connection / topology edges
3.  Route discovery — BFS: A→B→C returns [A, B, C]
4.  Multi-hop forwarding — packet passes through intermediate node B
5.  Packet delivery — receiver inbox receives the packet
6.  Attacker capture — attacker on an adjacent edge captures traffic
7.  No route → NoRouteError
8.  Loop-safe routing — cyclic graph doesn't infinite-loop
"""

import pytest

from backend.app.core.mesh_network import MeshNetwork, NoRouteError
from backend.app.core.mesh_node import MeshNode
from backend.app.core.mesh_packet import MeshPacket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def net() -> MeshNetwork:
    """Fresh MeshNetwork for each test."""
    return MeshNetwork()


def add_node(net: MeshNetwork, node_id: str, is_attacker: bool = False) -> MeshNode:
    node = MeshNode(node_id, is_attacker=is_attacker)
    net.add_node(node)
    return node


def make_packet(sender: str, receiver: str, payload: str = "test") -> MeshPacket:
    return MeshPacket(
        packet_id="pkt-test",
        sender_id=sender,
        receiver_id=receiver,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Scenario 1 — Node creation (≥3 nodes)
# ---------------------------------------------------------------------------


def test_node_creation_three_nodes(net: MeshNetwork):
    """Three nodes can be added and retrieved from the network."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    assert len(net.nodes) == 3
    assert "A" in net.nodes
    assert "B" in net.nodes
    assert "C" in net.nodes


# ---------------------------------------------------------------------------
# Scenario 2 — Node connection / topology
# ---------------------------------------------------------------------------


def test_node_connection_is_bidirectional(net: MeshNetwork):
    """connect_nodes creates edges in both directions."""
    add_node(net, "A")
    add_node(net, "B")
    net.connect_nodes("A", "B")
    assert "B" in net.nodes["A"].neighbors
    assert "A" in net.nodes["B"].neighbors


def test_topology_contains_correct_edges(net: MeshNetwork):
    """get_topology() reflects all added edges without duplication."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")
    topo = net.get_topology()
    edges = [tuple(sorted(e)) for e in topo["edges"]]
    assert ("A", "B") in edges
    assert ("B", "C") in edges
    assert len(topo["edges"]) == 2  # no duplicate edges


# ---------------------------------------------------------------------------
# Scenario 3 — Route discovery (BFS: A→B→C)
# ---------------------------------------------------------------------------


def test_bfs_direct_neighbors(net: MeshNetwork):
    """BFS returns [A, B] for directly connected nodes."""
    add_node(net, "A")
    add_node(net, "B")
    net.connect_nodes("A", "B")
    assert net.find_route("A", "B") == ["A", "B"]


def test_bfs_two_hop_route(net: MeshNetwork):
    """BFS finds [A, B, C] through an intermediate node."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")
    route = net.find_route("A", "C")
    assert route == ["A", "B", "C"]


def test_bfs_self_route(net: MeshNetwork):
    """Routing from a node to itself returns a single-element list."""
    add_node(net, "A")
    assert net.find_route("A", "A") == ["A"]


# ---------------------------------------------------------------------------
# Scenario 4 — Multi-hop forwarding (packet passes through B)
# ---------------------------------------------------------------------------


def test_multi_hop_forwarding_hop_log(net: MeshNetwork):
    """Forwarding A→C via B produces two HopRecords in the hop_log."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")

    pkt = make_packet("A", "C")
    net.send_packet(pkt)

    assert len(pkt.hop_log) == 2
    assert pkt.hop_log[0].from_node == "A"
    assert pkt.hop_log[0].to_node == "B"
    assert pkt.hop_log[1].from_node == "B"
    assert pkt.hop_log[1].to_node == "C"


def test_hop_numbers_are_sequential(net: MeshNetwork):
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")

    pkt = make_packet("A", "C")
    net.send_packet(pkt)

    assert pkt.hop_log[0].hop_number == 1
    assert pkt.hop_log[1].hop_number == 2


# ---------------------------------------------------------------------------
# Scenario 5 — Packet delivery (receiver inbox)
# ---------------------------------------------------------------------------


def test_packet_delivered_to_receiver_inbox(net: MeshNetwork):
    """After send_packet, the destination node holds the packet in its inbox."""
    add_node(net, "A")
    add_node(net, "B")
    net.connect_nodes("A", "B")

    pkt = make_packet("A", "B")
    net.send_packet(pkt)

    assert len(net.nodes["B"].inbox) == 1
    assert net.nodes["B"].inbox[0] is pkt


def test_sender_inbox_remains_empty(net: MeshNetwork):
    """The sender's inbox is not populated by send_packet."""
    add_node(net, "A")
    add_node(net, "B")
    net.connect_nodes("A", "B")

    pkt = make_packet("A", "B")
    net.send_packet(pkt)

    assert net.nodes["A"].inbox == []


# ---------------------------------------------------------------------------
# Scenario 6 — Attacker capture
# ---------------------------------------------------------------------------


def test_attacker_captures_adjacent_traffic(net: MeshNetwork):
    """
    ATTACKER connected to B captures traffic on the A→B→C route
    because it is a neighbor of B (a node on the route).
    """
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    add_node(net, "ATTACKER", is_attacker=True)
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")
    net.connect_nodes("ATTACKER", "B")  # adjacent to the route

    pkt = make_packet("A", "C", payload="secret")
    net.send_packet(pkt)

    attacker = net.nodes["ATTACKER"]
    assert len(attacker.captured_packets) >= 1
    assert attacker.captured_packets[0].payload == "secret"


def test_non_adjacent_attacker_does_not_capture(net: MeshNetwork):
    """
    An attacker with no neighbor on the route captures nothing.
    """
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    add_node(net, "ATTACKER", is_attacker=True)
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")
    # ATTACKER has no connection to A, B, or C

    pkt = make_packet("A", "C")
    net.send_packet(pkt)

    assert net.nodes["ATTACKER"].captured_packets == []


def test_attacker_does_not_receive_packet_in_inbox(net: MeshNetwork):
    """Capture should not affect the attacker's own inbox."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "ATTACKER", is_attacker=True)
    net.connect_nodes("A", "B")
    net.connect_nodes("ATTACKER", "A")

    pkt = make_packet("A", "B")
    net.send_packet(pkt)

    assert net.nodes["ATTACKER"].inbox == []


# ---------------------------------------------------------------------------
# Scenario 7 — No route → NoRouteError
# ---------------------------------------------------------------------------


def test_no_route_raises_no_route_error(net: MeshNetwork):
    """Sending to an unreachable node raises NoRouteError."""
    add_node(net, "A")
    add_node(net, "B")
    # No edge: A and B are isolated

    pkt = make_packet("A", "B")
    with pytest.raises(NoRouteError):
        net.send_packet(pkt)


def test_no_route_disjoint_components(net: MeshNetwork):
    """Two fully connected components with no bridge: NoRouteError across them."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    add_node(net, "D")
    net.connect_nodes("A", "B")
    net.connect_nodes("C", "D")  # separate island

    with pytest.raises(NoRouteError):
        net.find_route("A", "C")


# ---------------------------------------------------------------------------
# Scenario 8 — Loop-safe routing (cyclic graph)
# ---------------------------------------------------------------------------


def test_cyclic_graph_does_not_infinite_loop(net: MeshNetwork):
    """BFS on a cyclic graph terminates and returns the shortest path."""
    add_node(net, "A")
    add_node(net, "B")
    add_node(net, "C")
    add_node(net, "D")
    # Ring: A—B—C—D—A
    net.connect_nodes("A", "B")
    net.connect_nodes("B", "C")
    net.connect_nodes("C", "D")
    net.connect_nodes("D", "A")

    route = net.find_route("A", "C")
    assert route == ["A", "B", "C"]  # shortest path


def test_dense_cycle_find_route(net: MeshNetwork):
    """Fully-connected 4-node graph: always finds a route, no infinite loop."""
    for nid in ["A", "B", "C", "D"]:
        add_node(net, nid)
    for a in ["A", "B", "C", "D"]:
        for b in ["A", "B", "C", "D"]:
            if a < b:
                net.connect_nodes(a, b)

    route = net.find_route("A", "D")
    assert route[0] == "A"
    assert route[-1] == "D"


# ---------------------------------------------------------------------------
# reset() helper
# ---------------------------------------------------------------------------


def test_reset_clears_all_nodes(net: MeshNetwork):
    add_node(net, "A")
    add_node(net, "B")
    net.reset()
    assert net.nodes == {}
