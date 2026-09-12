"""Core security and utility abstractions."""

from backend.app.core.identity import generate_device_identity
from backend.app.core.registry import (
    DEFAULT_REGISTRY_PATH,
    register_member,
    get_member_by_rescue_id,
    get_member_by_device_id,
    is_member_active,
    revoke_member,
)
from backend.app.core.decryption_gate import (
    process_incoming_packet,
    log_security_event,
    SECURITY_LOGS,
)

__all__ = [
    "generate_device_identity",
    "DEFAULT_REGISTRY_PATH",
    "register_member",
    "get_member_by_rescue_id",
    "get_member_by_device_id",
    "is_member_active",
    "revoke_member",
    "process_incoming_packet",
    "log_security_event",
    "SECURITY_LOGS",
]

