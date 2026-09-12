"""
test_mesh_node.py — Unit tests for MeshNode in isolation.

These tests verify node construction, neighbor management,
packet reception, and attacker capture behaviour independently
of the MeshNetwork.
"""

import copy

import pytest

from backend.app.core.mesh_node import MeshNode
from backend.app.core.mesh_packet import MeshPacket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_packet(packet_id: str = "pkt-1", payload: str = "hello") -> MeshPacket:
    return MeshPacket(
        packet_id=packet_id,
        sender_id="NODE-A",
        receiver_id="NODE-B",
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_node_default_construction():
    node = MeshNode("NODE-X")
    assert node.node_id == "NODE-X"
    assert node.is_attacker is False
    assert node.neighbors == set()
    assert node.inbox == []
    assert node.captured_packets == []


def test_node_attacker_flag():
    node = MeshNode("EVIL", is_attacker=True)
    assert node.is_attacker is True


# ---------------------------------------------------------------------------
# Neighbor management
# ---------------------------------------------------------------------------


def test_add_neighbor():
    node = MeshNode("A")
    node.add_neighbor("B")
    assert "B" in node.neighbors


def test_add_multiple_neighbors():
    node = MeshNode("A")
    for n in ["B", "C", "D"]:
        node.add_neighbor(n)
    assert node.neighbors == {"B", "C", "D"}


def test_remove_neighbor():
    node = MeshNode("A")
    node.add_neighbor("B")
    node.remove_neighbor("B")
    assert "B" not in node.neighbors


def test_remove_nonexistent_neighbor_is_safe():
    node = MeshNode("A")
    node.remove_neighbor("GHOST")  # must not raise


# ---------------------------------------------------------------------------
# Packet reception
# ---------------------------------------------------------------------------


def test_receive_packet_adds_to_inbox():
    node = MeshNode("NODE-B")
    pkt = make_packet()
    node.receive_packet(pkt)
    assert len(node.inbox) == 1
    assert node.inbox[0] is pkt


def test_receive_multiple_packets():
    node = MeshNode("NODE-B")
    pkts = [make_packet(f"pkt-{i}") for i in range(3)]
    for p in pkts:
        node.receive_packet(p)
    assert len(node.inbox) == 3


# ---------------------------------------------------------------------------
# Attacker capture
# ---------------------------------------------------------------------------


def test_capture_packet_stores_copy():
    attacker = MeshNode("EVIL", is_attacker=True)
    pkt = make_packet()
    attacker.capture_packet(pkt)
    assert len(attacker.captured_packets) == 1


def test_capture_is_independent_of_original():
    """Mutations to the original packet after capture must not affect the copy."""
    attacker = MeshNode("EVIL", is_attacker=True)
    pkt = make_packet()
    attacker.capture_packet(pkt)

    # Mutate the original
    pkt.payload = "TAMPERED"

    captured = attacker.captured_packets[0]
    # The captured copy should still hold the original payload
    assert captured.payload == "hello"


def test_non_attacker_node_has_empty_captured():
    node = MeshNode("NODE-Z")
    pkt = make_packet()
    node.receive_packet(pkt)
    assert node.captured_packets == []


def test_capture_multiple_packets():
    attacker = MeshNode("EVIL", is_attacker=True)
    for i in range(5):
        attacker.capture_packet(make_packet(f"pkt-{i}"))
    assert len(attacker.captured_packets) == 5
