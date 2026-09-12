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


def build_demo_network() -> MeshNetwork:
    """
    Construct the standard 5-node Phase 4 demo topology and return it.

    Nodes:
        NODE-A  — normal
        NODE-B  — normal (central hub)
        NODE-C  — normal
        NODE-D  — normal
        NODE-E  — normal (destination in demo sends)
        ATTACKER — passive sniffer connected to NODE-B and NODE-C

    Edges:
        NODE-A  ↔ NODE-B
        NODE-B  ↔ NODE-C
        NODE-B  ↔ NODE-D
        NODE-C  ↔ NODE-E
        ATTACKER ↔ NODE-B   (sniffs NODE-A→…→NODE-E traffic)
        ATTACKER ↔ NODE-C

    Returns the populated (shared) MeshNetwork instance.
    """
    reset_network()

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
