import time
import uuid
from typing import Callable, List, Optional

from backend.app.core.crypto import (
    canonicalize_payload,
    decode_x25519_public_key_b64,
    encrypt_authenticated,
    sign_bytes,
)
from backend.app.core.decryption_gate import process_incoming_packet
from backend.app.core.mesh_network import MeshNetwork, NoRouteError
from backend.app.core.mesh_packet import MeshPacket
from backend.app.models.messages import (
    DecryptMessageResponse,
    InboxMessageSummary,
    SecureMessagePayload,
    SendMessageRequest,
    SendMessageResponse,
)
from backend.app.models.registry import MemberStatus, RescueMember
from backend.app.models.schemas import HopRecordSchema
from backend.app.services.crypto_service import (
    CryptoService,
    CryptoServiceError,
    crypto_service as default_crypto_service,
)
from backend.app.services.mesh_service import get_network as default_get_network
from backend.app.services.registry_service import (
    MemberNotFoundError,
    RegistryService,
    registry_service as default_registry_service,
)


class MessageServiceError(Exception):
    """Base exception for message service operations."""
    pass


class MemberNotActiveError(MessageServiceError):
    """Raised when a sender or recipient is revoked or not active."""
    pass


class MemberMissingKeysError(MessageServiceError):
    """Raised when sender or recipient lacks required cryptographic keys."""
    pass


class MeshNodeNotFoundError(MessageServiceError):
    """Raised when a resolved device ID is not registered in the active mesh network."""
    pass


class PacketNotFoundError(MessageServiceError):
    """Raised when a requested packet ID cannot be found in a device's inbox."""
    pass


class MessageService:
    """Orchestrates Phase 5 Secure Message Transmission & Phase 6 Controlled Decryption.

    Transmission Flow (Phase 5):
    1. Resolves administrative Rescue IDs or Device IDs to registered RescueMembers.
    2. Enforces active status and cryptographic key readiness on both parties.
    3. Authenticates and encrypts plaintext message via X25519 + ChaCha20-Poly1305 + HKDF-SHA256.
    4. Signs canonical metadata + ciphertext using sender's Ed25519 private key.
    5. Encapsulates secure payload (strictly NO plaintext) into an opaque MeshPacket.
    6. Routes and forwards packet across the software-simulated mesh network.

    Decryption Flow (Phase 6):
    1. Resolves recipient device and pulls encrypted packet from recipient inbox.
    2. Loads local recipient X25519 private key without exposing it to APIs or logs.
    3. Invokes Phase 6 authorization gate (registry lookup, active check, Ed25519 signature verification,
       recipient authorization check, replay protection, and ChaCha20-Poly1305 decryption).
    4. Releases plaintext only upon 100% verification success.
    """

    def __init__(
        self,
        registry_service_instance: Optional[RegistryService] = None,
        crypto_service_instance: Optional[CryptoService] = None,
        network_provider: Optional[Callable[[], MeshNetwork]] = None,
    ) -> None:
        self.registry_service = registry_service_instance or default_registry_service
        self.crypto_service = crypto_service_instance or default_crypto_service
        self.get_network = network_provider or default_get_network

    def resolve_member(self, identifier: str) -> RescueMember:
        """Resolves an identifier (Rescue ID like 'RESQ-001' or Device ID like 'DEVICE-001') to a RescueMember."""
        # Check by Rescue ID first
        member = self.registry_service.get_member_by_rescue_id(identifier)
        if member is None:
            # Fallback check by Device ID
            member = self.registry_service.get_member_by_device_id(identifier)
        if member is None:
            raise MemberNotFoundError(f"Member '{identifier}' not found in registry.")
        return member

    def send_secure_message(
        self,
        sender_id: str,
        recipient_id: str,
        message: str,
        priority: str = "NORMAL",
    ) -> SendMessageResponse:
        """Encrypts, signs, and dispatches an emergency message across the mesh network.

        Guarantees:
        - Plaintext message is strictly omitted from the transmitted MeshPacket.
        - Attacker nodes sniffing adjacent hops observe only ciphertext and cryptographic metadata.
        - Signature binds all immutable routing metadata and ciphertext.
        """
        # 1. Resolve Sender & Recipient Identities
        sender_member = self.resolve_member(sender_id)
        recipient_member = self.resolve_member(recipient_id)

        # 2. Validate Sender Active Status & Key Material
        if sender_member.status != MemberStatus.ACTIVE:
            raise MemberNotActiveError(
                f"Sender '{sender_id}' ({sender_member.rescue_id}) is revoked and cannot transmit messages."
            )
        if not sender_member.signing_public_key:
            raise MemberMissingKeysError(
                f"Sender '{sender_id}' ({sender_member.rescue_id}) has no signing public key in registry."
            )

        # Load sender Ed25519 private signing key from local disk
        sender_signing_priv = self.crypto_service.load_device_signing_private_key(
            sender_member.device_id
        )

        # 3. Validate Recipient Active Status & Key Material
        if recipient_member.status != MemberStatus.ACTIVE:
            raise MemberNotActiveError(
                f"Recipient '{recipient_id}' ({recipient_member.rescue_id}) is revoked and cannot receive messages."
            )
        if not recipient_member.encryption_public_key:
            raise MemberMissingKeysError(
                f"Recipient '{recipient_id}' ({recipient_member.rescue_id}) has no encryption public key in registry."
            )

        # Decode recipient X25519 public encryption key
        recipient_encryption_pub = decode_x25519_public_key_b64(
            recipient_member.encryption_public_key
        )

        # 4. Authenticated Encryption (X25519 + ChaCha20-Poly1305 + HKDF-SHA256)
        message_bytes = message.encode("utf-8")
        envelope = encrypt_authenticated(
            recipient_public_key=recipient_encryption_pub,
            plaintext=message_bytes,
        )

        # 5. Generate Packet and Message Identifiers
        packet_id = f"PKT-{uuid.uuid4().hex[:8].upper()}"
        message_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"

        # 6. Generate Deterministic Integer Timestamp
        timestamp = int(time.time())

        # 7. Construct and Sign Canonical Signature Dictionary
        # MUST match exact Phase 5/Phase 6 shared contract
        canonical_dict = {
            "ciphertext": envelope.ciphertext,
            "ephemeral_public_key": envelope.ephemeral_public_key,
            "message_id": message_id,
            "nonce": envelope.nonce,
            "packet_id": packet_id,
            "recipient_device_id": recipient_member.device_id,
            "recipient_rescue_id": recipient_member.rescue_id,
            "salt": envelope.salt,
            "sender_device_id": sender_member.device_id,
            "sender_rescue_id": sender_member.rescue_id,
            "timestamp": timestamp,
            "version": 1,
        }
        canonical_bytes = canonicalize_payload(canonical_dict)
        signature_b64 = sign_bytes(sender_signing_priv, canonical_bytes)

        # 8. Assemble SecureMessagePayload (NO PLAINTEXT)
        secure_payload = SecureMessagePayload(
            version=1,
            packet_id=packet_id,
            message_id=message_id,
            sender_rescue_id=sender_member.rescue_id,
            sender_device_id=sender_member.device_id,
            recipient_rescue_id=recipient_member.rescue_id,
            recipient_device_id=recipient_member.device_id,
            timestamp=timestamp,
            key_agreement=envelope.key_agreement,
            kdf=envelope.kdf,
            cipher=envelope.cipher,
            ephemeral_public_key=envelope.ephemeral_public_key,
            salt=envelope.salt,
            nonce=envelope.nonce,
            ciphertext=envelope.ciphertext,
            signature=signature_b64,
        )

        # 9. Encapsulate in MeshPacket
        mesh_packet = MeshPacket(
            packet_id=packet_id,
            sender_id=sender_member.device_id,
            receiver_id=recipient_member.device_id,
            payload=secure_payload.model_dump(),
        )

        # 10. Route and Forward via Existing MeshNetwork
        net = self.get_network()
        if sender_member.device_id not in net.nodes:
            raise MeshNodeNotFoundError(
                f"Sender device node '{sender_member.device_id}' is not registered in the mesh network."
            )
        if recipient_member.device_id not in net.nodes:
            raise MeshNodeNotFoundError(
                f"Recipient device node '{recipient_member.device_id}' is not registered in the mesh network."
            )

        # send_packet performs BFS routing and multi-hop forwarding
        net.send_packet(mesh_packet)

        # 11. Return Safe Response (NO PLAINTEXT)
        return SendMessageResponse(
            packet_id=mesh_packet.packet_id,
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            status="delivered",
            hop_log=[
                HopRecordSchema(
                    hop_number=h.hop_number,
                    from_node=h.from_node,
                    to_node=h.to_node,
                    timestamp=h.timestamp,
                )
                for h in mesh_packet.hop_log
            ],
            payload=secure_payload,
        )

    def get_inbox_messages(self, recipient_id: str) -> List[InboxMessageSummary]:
        """Retrieves all encrypted packets delivered to a recipient device's inbox."""
        recipient_member = self.resolve_member(recipient_id)
        net = self.get_network()

        if recipient_member.device_id not in net.nodes:
            return []

        node = net.nodes[recipient_member.device_id]
        summaries: List[InboxMessageSummary] = []

        for pkt in node.inbox:
            payload_data = pkt.payload
            if isinstance(payload_data, dict) and "ciphertext" in payload_data:
                try:
                    p = SecureMessagePayload(**payload_data)
                    summaries.append(
                        InboxMessageSummary(
                            packet_id=p.packet_id,
                            message_id=p.message_id,
                            sender_rescue_id=p.sender_rescue_id,
                            sender_device_id=p.sender_device_id,
                            recipient_rescue_id=p.recipient_rescue_id,
                            recipient_device_id=p.recipient_device_id,
                            timestamp=p.timestamp,
                            status="encrypted",
                            payload=p,
                        )
                    )
                except Exception:
                    continue

        return summaries

    def decrypt_inbox_message(
        self,
        recipient_id: str,
        packet_id: str,
    ) -> DecryptMessageResponse:
        """Processes an incoming inbox packet through the Phase 6 authorization & decryption gate."""
        recipient_member = self.resolve_member(recipient_id)
        net = self.get_network()

        if recipient_member.device_id not in net.nodes:
            raise MeshNodeNotFoundError(
                f"Recipient node '{recipient_member.device_id}' is not in the mesh network."
            )

        node = net.nodes[recipient_member.device_id]
        target_pkt = None
        for pkt in node.inbox:
            if pkt.packet_id == packet_id:
                target_pkt = pkt
                break

        if not target_pkt:
            raise PacketNotFoundError(
                f"Packet '{packet_id}' not found in inbox of {recipient_member.rescue_id} ({recipient_member.device_id})."
            )

        # Load recipient's private key locally
        recipient_priv_key = self.crypto_service.load_device_encryption_private_key(
            recipient_member.device_id
        )

        gate_result = process_incoming_packet(
            packet=target_pkt.payload,
            current_receiver_id=recipient_member.device_id,
            receiver_private_key=recipient_priv_key,
        )

        return DecryptMessageResponse(
            status=gate_result["status"],
            message=gate_result.get("message"),
            sender_name=gate_result.get("sender_name"),
            sender_id=gate_result.get("sender_id"),
            packet_id=gate_result.get("packet_id", packet_id),
            message_id=gate_result.get("message_id"),
            reason=gate_result.get("reason"),
        )

    def decrypt_direct_payload(
        self,
        recipient_id: str,
        payload: SecureMessagePayload,
    ) -> DecryptMessageResponse:
        """Directly passes a SecureMessagePayload through the Phase 6 gate for recipient_id."""
        recipient_member = self.resolve_member(recipient_id)
        recipient_priv_key = self.crypto_service.load_device_encryption_private_key(
            recipient_member.device_id
        )

        gate_result = process_incoming_packet(
            packet=payload.model_dump(),
            current_receiver_id=recipient_member.device_id,
            receiver_private_key=recipient_priv_key,
        )

        return DecryptMessageResponse(
            status=gate_result["status"],
            message=gate_result.get("message"),
            sender_name=gate_result.get("sender_name"),
            sender_id=gate_result.get("sender_id"),
            packet_id=gate_result.get("packet_id", payload.packet_id),
            message_id=gate_result.get("message_id", payload.message_id),
            reason=gate_result.get("reason"),
        )


# Default singleton service instance
message_service = MessageService()
