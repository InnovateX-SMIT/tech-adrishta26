"""
mesh_service.py — Application-level singleton for the shared MeshNetwork instance.

All API endpoints share one MeshNetwork via get_network().
reset_network() re-initialises the shared instance cleanly (used by demo and tests).
build_demo_network() wires up the standard 5-node Phase 4 topology.

Demo topology
─────────────
    NODE-A ─── NODE-B ─── NODE-C
                 │              │
              NODE-D        NODE-E
              (attacker)

  ATTACKER is connected to NODE-B and NODE-D so it can passively sniff
  traffic on the NODE-B ↔ NODE-D edge as well as any hop that traverses
  through that segment.
"""

from __future__ import annotations

from backend.app.core.mesh_network import MeshNetwork
from backend.app.core.mesh_node import MeshNode

# Module-level singleton
_network: MeshNetwork = MeshNetwork()


def get_network() -> MeshNetwork:
    """Return the shared MeshNetwork instance used by all API endpoints."""
    return _network


def reset_network() -> None:
    """
    Reset the shared MeshNetwork to an empty state.

    Safe to call from tests or the demo endpoint — replaces the singleton
    contents in-place so that existing references remain valid.
    """
    _network.reset()


def build_demo_network(use_device_ids: bool = False) -> MeshNetwork:
    """
    Construct the standard 5-node Phase 4 demo topology and return it.

    If use_device_ids is True, uses Phase 2 naming convention:
        DEVICE-001 through DEVICE-005 + ATTACKER
    Otherwise uses default:
        NODE-A through NODE-E + ATTACKER
    """
    reset_network()

    if use_device_ids:
        nodes = [
            MeshNode("DEVICE-001"),
            MeshNode("DEVICE-002"),
            MeshNode("DEVICE-003"),
            MeshNode("DEVICE-004"),
            MeshNode("DEVICE-005"),
            MeshNode("ATTACKER", is_attacker=True),
        ]
        for node in nodes:
            _network.add_node(node)

        _network.connect_nodes("DEVICE-001", "DEVICE-002")
        _network.connect_nodes("DEVICE-002", "DEVICE-003")
        _network.connect_nodes("DEVICE-002", "DEVICE-004")
        _network.connect_nodes("DEVICE-003", "DEVICE-005")
        _network.connect_nodes("ATTACKER", "DEVICE-002")
        _network.connect_nodes("ATTACKER", "DEVICE-003")
        return _network

    node_a = MeshNode("NODE-A")
    node_b = MeshNode("NODE-B")
    node_c = MeshNode("NODE-C")
    node_d = MeshNode("NODE-D")
    node_e = MeshNode("NODE-E")
    attacker = MeshNode("ATTACKER", is_attacker=True)

    for node in (node_a, node_b, node_c, node_d, node_e, attacker):
        _network.add_node(node)

    _network.connect_nodes("NODE-A", "NODE-B")
    _network.connect_nodes("NODE-B", "NODE-C")
    _network.connect_nodes("NODE-B", "NODE-D")
    _network.connect_nodes("NODE-C", "NODE-E")
    _network.connect_nodes("ATTACKER", "NODE-B")
    _network.connect_nodes("ATTACKER", "NODE-C")

    return _network
