"""
mesh_network.py — Network topology and packet-routing for the RESQ mesh simulation.

Design decisions:
- BFS routing: deterministic, loop-safe (visited set), raises NoRouteError on failure.
- Attacker model: when a node with is_attacker=True exists on the route, it
  captures a copy of the packet when traffic transits ANY edge that the attacker
  node is a neighbor of.  This simulates passive sniffing of the shared medium
  rather than the attacker being a destination.  Phase 7 will reuse this exact
  behaviour to contrast vulnerable vs. encrypted traffic.
- hop_log is written directly onto the packet so delivery history is self-contained.
- No crypto, no auth, no persistence — pure in-memory simulation.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from dataclasses import dataclass, field
from .mesh_node import MeshNode
from .mesh_packet import HopRecord, MeshPacket


class NoRouteError(Exception):
    """Raised when BFS finds no path between source and destination."""


@dataclass
class DeliveryLogEntry:
    """Records an end-to-end packet delivery attempt across the mesh."""

    packet_id: str
    source: str
    destination: str
    route: list[str]
    hops: list[HopRecord]
    status: str  # "delivered" or "failed"
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MeshNetwork:
    """
    In-memory mesh network: manages topology, routing, and packet forwarding.

    Attributes:
        nodes: dict mapping node_id → MeshNode for all registered nodes.
        delivery_logs: ordered audit trail of packet routing attempts.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, MeshNode] = {}
        self.delivery_logs: list[DeliveryLogEntry] = []

    # ------------------------------------------------------------------
    # Topology management
    # ------------------------------------------------------------------

    def add_node(self, node: MeshNode) -> None:
        """Register a node with the network."""
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove a node and cleanly unregister it from all neighbors."""
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id!r} not found in mesh network.")
        # Disconnect from all direct neighbors
        target = self.nodes[node_id]
        for neighbor_id in list(target.neighbors):
            if neighbor_id in self.nodes:
                self.nodes[neighbor_id].remove_neighbor(node_id)
        del self.nodes[node_id]

    def connect_nodes(self, a_id: str, b_id: str) -> None:
        """
        Create a bidirectional link between two nodes.

        Raises:
            KeyError: if either node ID is not registered.
        """
        a = self.nodes[a_id]
        b = self.nodes[b_id]
        a.add_neighbor(b_id)
        b.add_neighbor(a_id)

    def disconnect_nodes(self, a_id: str, b_id: str) -> None:
        """
        Sever the bidirectional link between two nodes.

        Raises:
            KeyError: if either node ID is not registered.
        """
        a = self.nodes[a_id]
        b = self.nodes[b_id]
        a.remove_neighbor(b_id)
        b.remove_neighbor(a_id)

    def has_connection(self, a_id: str, b_id: str) -> bool:
        """Return True if a direct bidirectional edge exists between a and b."""
        if a_id not in self.nodes or b_id not in self.nodes:
            return False
        return b_id in self.nodes[a_id].neighbors and a_id in self.nodes[b_id].neighbors

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return a sorted list of direct neighbor IDs for a node."""
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id!r} not found in mesh network.")
        return sorted(self.nodes[node_id].neighbors)

    def get_topology(self) -> dict:
        """
        Return a serialisable snapshot of the current topology.

        Returns:
            {
                "nodes": [{"node_id": ..., "neighbors": [...], "is_attacker": bool}, ...],
                "edges": [[a_id, b_id], ...]   # deduplicated
            }
        """
        edges: set[tuple[str, str]] = set()
        node_list = []
        for node in self.nodes.values():
            node_list.append(
                {
                    "node_id": node.node_id,
                    "neighbors": sorted(node.neighbors),
                    "is_attacker": node.is_attacker,
                }
            )
            for nbr in node.neighbors:
                edge = tuple(sorted([node.node_id, nbr]))
                edges.add(edge)  # type: ignore[arg-type]

        return {
            "nodes": node_list,
            "edges": [list(e) for e in sorted(edges)],
        }

    def reset(self) -> None:
        """Clear all nodes, edges, and delivery logs."""
        self.nodes.clear()
        self.delivery_logs.clear()

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def find_route(self, source_id: str, dest_id: str) -> list[str]:
        """
        BFS shortest-path discovery from source to dest.

        Returns:
            Ordered list of node IDs from source to dest (inclusive).

        Raises:
            NoRouteError: if dest is unreachable from source.
            KeyError:     if source or dest is not a registered node.
        """
        if source_id not in self.nodes:
            raise KeyError(f"Source node {source_id!r} not found in the mesh.")
        if dest_id not in self.nodes:
            raise KeyError(f"Destination node {dest_id!r} not found in the mesh.")

        if source_id == dest_id:
            return [source_id]

        visited: set[str] = {source_id}
        queue: deque[list[str]] = deque([[source_id]])

        while queue:
            path = queue.popleft()
            current_id = path[-1]
            current_node = self.nodes[current_id]

            # Sort neighbors to ensure deterministic BFS path discovery
            for neighbor_id in sorted(current_node.neighbors):
                if neighbor_id == dest_id:
                    return path + [dest_id]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(path + [neighbor_id])

        raise NoRouteError(
            f"No route found from {source_id!r} to {dest_id!r}"
        )

    # ------------------------------------------------------------------
    # Packet forwarding & logging
    # ------------------------------------------------------------------

    def send_packet(self, packet: MeshPacket) -> MeshPacket:
        """
        High-level send: discover route and forward hop-by-hop.

        Returns:
            The same packet instance with hop_log fully populated.

        Raises:
            NoRouteError: if no path exists.
            KeyError:     if sender or receiver node is unknown.
        """
        try:
            route = self.find_route(packet.sender_id, packet.receiver_id)
            self.forward_packet(packet, route)
            self._record_log(
                packet_id=packet.packet_id,
                source=packet.sender_id,
                destination=packet.receiver_id,
                route=route,
                hops=list(packet.hop_log),
                status="delivered",
            )
            return packet
        except NoRouteError as exc:
            self._record_log(
                packet_id=packet.packet_id,
                source=packet.sender_id,
                destination=packet.receiver_id,
                route=[],
                hops=[],
                status="failed",
                error=str(exc),
            )
            raise

    def _record_log(
        self,
        packet_id: str,
        source: str,
        destination: str,
        route: list[str],
        hops: list[HopRecord],
        status: str,
        error: str | None = None,
    ) -> None:
        self.delivery_logs.append(
            DeliveryLogEntry(
                packet_id=packet_id,
                source=source,
                destination=destination,
                route=route,
                hops=hops,
                status=status,
                error=error,
            )
        )

    def get_delivery_logs(self) -> list[DeliveryLogEntry]:
        """Return the list of all delivery logs recorded by the network."""
        return list(self.delivery_logs)

    def clear_delivery_logs(self) -> None:
        """Clear recorded delivery logs."""
        self.delivery_logs.clear()

    def forward_packet(self, packet: MeshPacket, route: list[str]) -> None:
        """
        Execute hop-by-hop traversal along *route*, appending HopRecords and
        triggering attacker capture where applicable.

        Attacker sniffing model (Phase 7 compatible):
            For each hop (from_node → to_node), ANY node that is:
              - an attacker (is_attacker=True), AND
              - a neighbor of EITHER from_node OR to_node
            will capture a copy of the packet before delivery.
            This models passive medium sniffing — the attacker observes traffic
            on links it is adjacent to, regardless of whether it is the next hop.

        Args:
            packet: MeshPacket to forward.
            route:  Ordered list of node IDs [source, ..., dest].
        """
        for hop_index in range(len(route) - 1):
            from_id = route[hop_index]
            to_id = route[hop_index + 1]
            timestamp = datetime.now(timezone.utc).isoformat()

            hop_record = HopRecord(
                hop_number=hop_index + 1,
                from_node=from_id,
                to_node=to_id,
                timestamp=timestamp,
            )
            packet.hop_log.append(hop_record)

            # Attacker sniffing: capture if any registered attacker node is
            # adjacent to this hop's edge (i.e. neighbors from_id or to_id).
            for node in self.nodes.values():
                if node.is_attacker and node.node_id != from_id and node.node_id != to_id:
                    if from_id in node.neighbors or to_id in node.neighbors:
                        node.capture_packet(packet)

        # Deliver to destination
        dest_node = self.nodes[route[-1]]
        dest_node.receive_packet(packet)
