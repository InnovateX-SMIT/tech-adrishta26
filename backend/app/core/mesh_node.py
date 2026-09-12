"""
mesh_node.py — Individual node in the RESQ mesh simulation.

A MeshNode models a single participant in the mesh network.
It holds an inbox for delivered packets and an optional attacker
inbox for sniffed/captured packets (when is_attacker=True).

No cryptographic logic lives here — Phase 5+ adds that above this layer.
"""

from __future__ import annotations

import copy

from .mesh_packet import MeshPacket


class MeshNode:
    """
    Represents a single node in the mesh network.

    Attributes:
        node_id:           Unique string identifier.
        neighbors:         Set of directly connected node IDs (not object refs,
                           to avoid circular dependencies with MeshNetwork).
        inbox:             Packets successfully delivered to this node.
        captured_packets:  Packets observed/sniffed by this node (attacker mode).
        is_attacker:       When True, the network will call capture_packet() for
                           traffic that passes through this node's edges.
    """

    def __init__(self, node_id: str, is_attacker: bool = False) -> None:
        self.node_id: str = node_id
        self.neighbors: set[str] = set()
        self.inbox: list[MeshPacket] = []
        self.captured_packets: list[MeshPacket] = []
        self.is_attacker: bool = is_attacker

    # ------------------------------------------------------------------
    # Connectivity helpers (called by MeshNetwork, not directly by users)
    # ------------------------------------------------------------------

    def add_neighbor(self, node_id: str) -> None:
        """Register a direct neighbor by ID."""
        self.neighbors.add(node_id)

    def remove_neighbor(self, node_id: str) -> None:
        """Remove a direct neighbor by ID (if present)."""
        self.neighbors.discard(node_id)

    # ------------------------------------------------------------------
    # Packet reception
    # ------------------------------------------------------------------

    def receive_packet(self, packet: MeshPacket) -> None:
        """Accept a delivered packet into this node's inbox."""
        self.inbox.append(packet)

    def capture_packet(self, packet: MeshPacket) -> None:
        """
        Record a copy of an observed packet (attacker / sniffer behaviour).

        The network calls this when traffic transits an edge adjacent to
        this attacker node, before the packet is delivered to the real
        destination.  A shallow copy is stored so attacker state is
        independent of later mutations to the packet's hop_log.
        """
        import copy
        self.captured_packets.append(copy.copy(packet))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"MeshNode(id={self.node_id!r}, neighbors={self.neighbors!r}, "
            f"attacker={self.is_attacker})"
        )
