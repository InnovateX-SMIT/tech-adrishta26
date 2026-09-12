import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.config import settings
from backend.app.models.messages import (
    MessageRecord,
    MessageStatus,
    build_conversation_id,
)
from backend.app.storage.json_store import load_json, save_json


class MessageRepositoryError(Exception):
    """Base exception for message repository operations."""
    pass


class MessageNotFoundError(MessageRepositoryError):
    """Raised when a message record is not found."""
    pass


class MessageRepository:
    """Atomic, thread-safe persistent store for Phase 5 emergency message records.

    CONFIDENTIALITY GUARANTEE:
    Stores exclusively authenticated encryption envelopes (ciphertext, nonce, salt,
    ephemeral public key, Ed25519 signature) and metadata.
    Plaintext message content is strictly forbidden from being written to disk.
    """

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or (settings.data_dir / "messages.json")
        self._lock = threading.RLock()

    def _load_raw_data(self) -> Dict[str, Any]:
        default_data = {"version": 1, "messages": []}
        data = load_json(self.filepath, default=default_data)
        if not isinstance(data, dict):
            data = default_data
        if "messages" not in data or not isinstance(data["messages"], list):
            data["messages"] = []
        if "version" not in data:
            data["version"] = 1
        return data

    def _save_raw_data(self, data: Dict[str, Any]) -> None:
        save_json(self.filepath, data)

    def save_message(self, record: MessageRecord) -> MessageRecord:
        """Persists a new or updated MessageRecord to disk atomically."""
        with self._lock:
            data = self._load_raw_data()
            serialized = record.model_dump()

            # Strict security verification: ensure no plaintext leakage
            for forbidden_key in ("plaintext", "content", "decrypted_message", "message"):
                if forbidden_key in serialized:
                    raise MessageRepositoryError(
                        f"Security violation: Plaintext key '{forbidden_key}' detected in MessageRecord serialization!"
                    )

            # Check if record already exists (update in place) or append new
            updated = False
            for idx, item in enumerate(data["messages"]):
                if item.get("message_id") == record.message_id:
                    data["messages"][idx] = serialized
                    updated = True
                    break

            if not updated:
                data["messages"].append(serialized)

            self._save_raw_data(data)
            return record

    def get_message(self, message_id: str) -> Optional[MessageRecord]:
        """Retrieves a message record by its unique message_id."""
        with self._lock:
            data = self._load_raw_data()
            for item in data["messages"]:
                if item.get("message_id") == message_id:
                    return MessageRecord(**item)
            return None

    def get_message_by_packet_id(self, packet_id: str) -> Optional[MessageRecord]:
        """Retrieves a message record by its associated packet_id."""
        with self._lock:
            data = self._load_raw_data()
            for item in data["messages"]:
                if item.get("packet_id") == packet_id:
                    return MessageRecord(**item)
            return None

    def update_status(
        self,
        message_id: str,
        status: MessageStatus,
        delivered_at: Optional[float] = None,
        decrypted_at: Optional[float] = None,
        failure_reason: Optional[str] = None,
        hop_count: Optional[int] = None,
        route: Optional[List[str]] = None,
        packet_id: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> Optional[MessageRecord]:
        """Updates lifecycle status and timestamps on an existing record."""
        with self._lock:
            record = self.get_message(message_id)
            if not record:
                return None

            update_data = record.model_dump()
            update_data["status"] = status.value if hasattr(status, "value") else str(status)

            if delivered_at is not None:
                update_data["delivered_at"] = delivered_at
            if decrypted_at is not None:
                update_data["decrypted_at"] = decrypted_at
            if failure_reason is not None:
                update_data["failure_reason"] = failure_reason
            if hop_count is not None:
                update_data["hop_count"] = hop_count
            if route is not None:
                update_data["route"] = route
            if packet_id is not None:
                update_data["packet_id"] = packet_id
            if retry_count is not None:
                update_data["retry_count"] = retry_count

            updated_record = MessageRecord(**update_data)
            return self.save_message(updated_record)

    def list_messages_for_device(self, device_id: str) -> List[MessageRecord]:
        """Lists all message records sent by or addressed to the specified device ID."""
        target = device_id.strip().upper()
        with self._lock:
            data = self._load_raw_data()
            records: List[MessageRecord] = []
            for item in data["messages"]:
                s_dev = item.get("sender_device_id", "").strip().upper()
                r_dev = item.get("recipient_device_id", "").strip().upper()
                s_resq = item.get("sender_rescue_id", "").strip().upper()
                r_resq = item.get("recipient_rescue_id", "").strip().upper()
                if target in (s_dev, r_dev, s_resq, r_resq):
                    records.append(MessageRecord(**item))
            records.sort(key=lambda r: r.created_at)
            return records

    def get_conversation(self, device_a_id: str, device_b_id: str) -> List[MessageRecord]:
        """Retrieves bidirectional message thread between two devices."""
        conv_id = build_conversation_id(device_a_id, device_b_id)
        with self._lock:
            data = self._load_raw_data()
            records: List[MessageRecord] = []
            for item in data["messages"]:
                if item.get("conversation_id") == conv_id:
                    records.append(MessageRecord(**item))
            records.sort(key=lambda r: r.created_at)
            return records

    def clear(self) -> None:
        """Clears all message records (used for test isolation)."""
        with self._lock:
            self._save_raw_data({"version": 1, "messages": []})


# Default singleton instance
message_repository = MessageRepository()
