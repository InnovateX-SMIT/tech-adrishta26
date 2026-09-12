"""
mesh_packet.py — Core data structures for the RESQ mesh simulation layer.

MeshPacket and HopRecord are intentionally kept payload-agnostic:
- Phase 4: payload is plain text (str)
- Phase 5+: payload will be ciphertext/dict; no changes needed here
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class HopRecord:
    """Records a single traversal hop across the mesh."""

    hop_number: int
    from_node: str
    to_node: str
    timestamp: str  # ISO 8601


@dataclass
class MeshPacket:
    """
    An opaque message unit routed across a MeshNetwork.

    Attributes:
        packet_id:   Unique identifier for this packet.
        sender_id:   Node ID that originated the packet.
        receiver_id: Intended destination node ID.
        payload:     Opaque content — plain text in Phase 4, ciphertext in Phase 5+.
        created_at:  ISO 8601 creation timestamp.
        hop_log:     Ordered list of HopRecords appended as the packet traverses nodes.
    """

    packet_id: str
    sender_id: str = ""
    receiver_id: str = ""
    payload: Any = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hop_log: list[HopRecord] = field(default_factory=list)

    def __init__(
        self,
        packet_id: str,
        sender_id: str = "",
        receiver_id: str = "",
        payload: Any = None,
        created_at: Any = None,
        hop_log: Any = None,
        *,
        source: Any = None,
        destination: Any = None,
    ) -> None:
        self.packet_id = packet_id
        self.sender_id = sender_id or source or ""
        self.receiver_id = receiver_id or destination or ""
        self.payload = payload
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.hop_log = hop_log if hop_log is not None else []

    @property
    def source(self) -> str:
        """Alias for sender_id (Phase 4 requirement compliance)."""
        return self.sender_id

    @property
    def destination(self) -> str:
        """Alias for receiver_id (Phase 4 requirement compliance)."""
        return self.receiver_id
