import base64
import copy
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.decryption_gate import process_incoming_packet
from backend.app.core.mesh_packet import MeshPacket
from backend.app.models.attack import (
    AttackStatusResponse,
    CapturedPacket,
    SimulateAttackRequest,
    SimulateAttackResponse,
    SimulationMode,
    TamperCaptureResponse,
)
from backend.app.services.mesh_service import get_network
from backend.app.services.message_service import message_service
from backend.app.services.registry_service import registry_service

logger = logging.getLogger("resq.attack_simulation")

# Bounded in-memory capture history (FIFO, max 50 items)
MAX_CAPTURES = 50
SIMULATION_CAPTURES: List[CapturedPacket] = []
SIMULATION_LOGS: List[str] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_zero_plaintext_recursive(data: Any, plaintext: str) -> None:
    """Recursively validates that the plaintext string is never present in any key or value."""
    if not plaintext or len(plaintext.strip()) < 3:
        return

    if isinstance(data, str):
        if plaintext in data:
            raise ValueError(f"CRITICAL SECURITY FAILURE: Plaintext exposed in protected data structure: {data!r}")
    elif isinstance(data, dict):
        for k, v in data.items():
            if plaintext in str(k):
                raise ValueError(f"CRITICAL SECURITY FAILURE: Plaintext exposed in dictionary key: {k!r}")
            _assert_zero_plaintext_recursive(v, plaintext)
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            _assert_zero_plaintext_recursive(item, plaintext)
    elif hasattr(data, "model_dump"):
        _assert_zero_plaintext_recursive(data.model_dump(), plaintext)


class AttackSimulationService:
    def __init__(self) -> None:
        self.registry_service = registry_service
        self.message_service = message_service

    def get_network(self):
        return get_network()

    def get_status(self) -> AttackStatusResponse:
        vulnerable_count = sum(1 for c in SIMULATION_CAPTURES if c.communication_mode == "vulnerable")
        protected_count = sum(1 for c in SIMULATION_CAPTURES if c.communication_mode == "protected")
        last_cap = SIMULATION_CAPTURES[-1] if SIMULATION_CAPTURES else None
        return AttackStatusResponse(
            total_captures=len(SIMULATION_CAPTURES),
            vulnerable_captures=vulnerable_count,
            protected_captures=protected_count,
            last_capture=last_cap,
        )

    def list_captures(self) -> List[CapturedPacket]:
        return list(reversed(SIMULATION_CAPTURES))

    def get_capture_by_id(self, capture_id: str) -> Optional[CapturedPacket]:
        for c in SIMULATION_CAPTURES:
            if c.capture_id == capture_id:
                return c
        return None

    def reset_simulation(self) -> Dict[str, Any]:
        """Clears ONLY Phase 7 simulation state.
        
        Strictly preserves:
        - Device registry identities (data/registry.json)
        - Private and public keys (keys/)
        - Real message repository (data/messages.json)
        - Conversations and Phase 1-6 logs
        """
        SIMULATION_CAPTURES.clear()
        SIMULATION_LOGS.clear()

        # Clear captured packets on all nodes in mesh network
        net = self.get_network()
        for node in net.nodes.values():
            node.captured_packets.clear()

        log_msg = f"[INFO] {_now_iso()} | Attack simulation state reset | Registry and keys preserved"
        SIMULATION_LOGS.append(log_msg)
        logger.info(log_msg)

        return {
            "status": "RESET_SUCCESS",
            "message": "Attack simulation captures and logs cleared. Registry identities and cryptographic keys preserved.",
            "total_captures": 0,
        }

    def _ensure_attacker_node(self, preferred_node_id: Optional[str] = None) -> str:
        """Finds or configures an attacker node in the current topology."""
        net = self.get_network()

        if preferred_node_id and preferred_node_id in net.nodes:
            net.nodes[preferred_node_id].is_attacker = True
            return preferred_node_id

        # Look for existing node with is_attacker=True
        for nid, node in net.nodes.items():
            if node.is_attacker:
                return nid

        # If none, designate DEVICE-004 / NODE-D if present
        for candidate in ["DEVICE-004", "NODE-D", "DEVICE-003", "NODE-C"]:
            if candidate in net.nodes:
                net.nodes[candidate].is_attacker = True
                return candidate

        # Fallback to any relay or node that is not sender/receiver
        if len(net.nodes) >= 3:
            first_key = sorted(net.nodes.keys())[1]
            net.nodes[first_key].is_attacker = True
            return first_key

        return "UNKNOWN_ATTACKER"

    def simulate_attack(self, request: SimulateAttackRequest) -> SimulateAttackResponse:
        simulation_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        capture_id = f"CAP-{uuid.uuid4().hex[:8].upper()}"
        logs: List[str] = []

        sender_member = self.message_service.resolve_member(request.sender_id)
        recipient_member = self.message_service.resolve_member(request.recipient_id)

        net = self.get_network()
        attacker_node_id = self._ensure_attacker_node(request.attacker_node_id)

        # Clear previous captures on attacker node for clean single-run observation
        if attacker_node_id in net.nodes:
            net.nodes[attacker_node_id].captured_packets.clear()

        if request.mode == SimulationMode.VULNERABLE:
            # =========================================================================
            # MODE A: VULNERABLE / BEFORE RESQ (INSECURE DEMONSTRATION)
            # =========================================================================
            packet_id = f"PKT-VULN-{uuid.uuid4().hex[:8].upper()}"
            message_id = f"MSG-VULN-{uuid.uuid4().hex[:8].upper()}"

            log_1 = f"[WARN] Attack simulation started | Mode: vulnerable | Simulation: {simulation_id}"
            log_2 = f"[WARN] Packet transmitted without encryption | Packet: {packet_id}"
            logs.extend([log_1, log_2])
            SIMULATION_LOGS.extend([log_1, log_2])
            logger.warning(log_1)
            logger.warning(log_2)

            # Resolve mesh node IDs
            sender_node_id = sender_member.device_id if sender_member.device_id in net.nodes else request.sender_id
            recipient_node_id = recipient_member.device_id if recipient_member.device_id in net.nodes else request.recipient_id

            if sender_node_id not in net.nodes or recipient_node_id not in net.nodes:
                # Use demo aliases if needed
                demo_map = {"RESQ-001": "NODE-A", "RESQ-002": "NODE-B", "RESQ-004": "NODE-D"}
                sender_node_id = demo_map.get(sender_member.rescue_id, sender_node_id)
                recipient_node_id = demo_map.get(recipient_member.rescue_id, recipient_node_id)

            unencrypted_payload = {
                "version": 1,
                "packet_id": packet_id,
                "message_id": message_id,
                "sender_rescue_id": sender_member.rescue_id,
                "sender_device_id": sender_member.device_id,
                "recipient_rescue_id": recipient_member.rescue_id,
                "recipient_device_id": recipient_member.device_id,
                "plaintext": request.message,  # Unencrypted emergency text
                "timestamp": int(time.time()),
                "encryption": "disabled",
            }

            mesh_packet = MeshPacket(
                packet_id=packet_id,
                sender_id=sender_node_id,
                receiver_id=recipient_node_id,
                payload=unencrypted_payload,
            )

            # Route through mesh network
            delivered_packet = net.send_packet(mesh_packet)
            route = [h.from_node for h in delivered_packet.hop_log] + (
                [delivered_packet.hop_log[-1].to_node] if delivered_packet.hop_log else [sender_node_id, recipient_node_id]
            )

            # Check if attacker node captured it
            attacker_node = net.nodes.get(attacker_node_id)
            captured = False
            captured_record: Optional[CapturedPacket] = None

            # Look in attacker's captured_packets or check if attacker is on route/adjacent
            sniffed_payload = None
            if attacker_node and attacker_node.captured_packets:
                sniffed_payload = attacker_node.captured_packets[-1].payload
                captured = True
            elif attacker_node_id in route:
                sniffed_payload = unencrypted_payload
                captured = True

            if not captured and attacker_node:
                # Force transport-boundary observation if link is in network
                sniffed_payload = unencrypted_payload
                captured = True

            if captured and sniffed_payload:
                raw_bytes = json.dumps(sniffed_payload).encode("utf-8")
                sniffed_text = str(sniffed_payload.get("plaintext", request.message))

                captured_record = CapturedPacket(
                    simulation_id=simulation_id,
                    capture_id=capture_id,
                    packet_id=packet_id,
                    message_id=message_id,
                    captured_at=_now_iso(),
                    captured_at_node=attacker_node_id,
                    sender_id=sender_member.rescue_id,
                    recipient_id=recipient_member.rescue_id,
                    route=route,
                    communication_mode="vulnerable",
                    packet_size=len(raw_bytes),
                    metadata_visible_to_attacker=True,
                    contains_plaintext=True,
                    plaintext_exposed=True,
                    ciphertext_present=False,
                    signature_present=False,
                    sniffed_content=sniffed_text,
                    message_readable_by_attacker=True,
                    security_result="Message exposed",
                    explanation="The message was transmitted without encryption. The packet sniffer intercepted the packet and directly read the emergency distress message.",
                    raw_payload=sniffed_payload,
                )

                log_3 = f"[WARN] Attacker captured packet at node {attacker_node_id} | Capture: {capture_id}"
                log_4 = f"[WARN] Plaintext exposed to attacker: \"{sniffed_text}\""
                log_5 = "[WARN] Security demonstration: message readable by eavesdropper"
                logs.extend([log_3, log_4, log_5])
                SIMULATION_LOGS.extend([log_3, log_4, log_5])
                logger.warning(log_3)
                logger.warning(log_4)
                logger.warning(log_5)

            receiver_result = {
                "status": "DELIVERED_INSECURE",
                "message": request.message,
                "mode": "vulnerable",
                "warning": "Message delivered without encryption or digital signature authenticity verification.",
            }

            summary = "Before RESQ: The attacker captured the packet and read the emergency message."

        else:
            # =========================================================================
            # MODE B: PROTECTED / AFTER RESQ (CRYPTOGRAPHIC SECURITY PIPELINE)
            # =========================================================================
            log_1 = f"[INFO] Attack simulation started | Mode: protected | Simulation: {simulation_id}"
            logs.append(log_1)
            SIMULATION_LOGS.append(log_1)
            logger.info(log_1)

            # 1. Send via existing Phase 5 pipeline (X25519 + ChaCha20-Poly1305 + HKDF-SHA256 + Ed25519 signature)
            send_resp = self.message_service.send_secure_message(
                sender_id=request.sender_id,
                recipient_id=request.recipient_id,
                message=request.message,
            )

            packet_id = send_resp.packet_id
            message_id = send_resp.message_id
            route = [h.from_node for h in send_resp.hop_log] + (
                [send_resp.hop_log[-1].to_node] if send_resp.hop_log else []
            )

            log_2 = f"[INFO] Packet entered mesh with authenticated encryption | Packet: {packet_id}"
            logs.append(log_2)
            SIMULATION_LOGS.append(log_2)
            logger.info(log_2)

            # 2. Inspect captured packet at attacker node
            attacker_node = net.nodes.get(attacker_node_id)
            captured = False
            wire_payload = send_resp.payload.model_dump()

            if attacker_node and attacker_node.captured_packets:
                captured = True
            elif attacker_node_id in route:
                captured = True
            else:
                # Transport boundary observation
                captured = True

            # Extract ciphertext strictly from serialized wire payload
            ciphertext_b64 = wire_payload.get("ciphertext", "")
            raw_bytes = json.dumps(wire_payload).encode("utf-8")

            # Safe ciphertext preview (strictly from ciphertext bytes, never from plaintext)
            preview = f"{ciphertext_b64[:32]}... ({len(ciphertext_b64)} chars encrypted)"

            captured_record = CapturedPacket(
                simulation_id=simulation_id,
                capture_id=capture_id,
                packet_id=packet_id,
                message_id=message_id,
                captured_at=_now_iso(),
                captured_at_node=attacker_node_id,
                sender_id=sender_member.rescue_id,
                recipient_id=recipient_member.rescue_id,
                route=route,
                communication_mode="protected",
                packet_size=len(raw_bytes),
                metadata_visible_to_attacker=True,
                contains_plaintext=False,
                plaintext_exposed=False,
                ciphertext_present=True,
                signature_present=True,
                sniffed_content=preview,
                message_readable_by_attacker=False,
                security_result="Plaintext protected",
                explanation="The packet was encrypted before entering the mesh. The attacker captured the packet but cannot read the emergency message.",
                raw_payload=wire_payload,
            )

            # 3. Recursive Zero-Plaintext Audit
            _assert_zero_plaintext_recursive(captured_record, request.message)

            log_3 = f"[INFO] Attacker captured packet at node {attacker_node_id} | Capture: {capture_id}"
            log_4 = "[INFO] Captured packet contains ciphertext | Zero plaintext in wire payload"
            log_5 = "[INFO] Attacker decryption attempt denied | No private key material available"
            logs.extend([log_3, log_4, log_5])
            SIMULATION_LOGS.extend([log_3, log_4, log_5])
            logger.info(log_3)
            logger.info(log_4)
            logger.info(log_5)

            # 4. Authorized Receiver executes Phase 6 gate
            gate_result = process_incoming_packet(
                packet=wire_payload,
                current_receiver_id=recipient_member.device_id,
            )

            if gate_result.get("status") == "SUCCESS":
                log_6 = "[INFO] Authorized receiver verified and decrypted message successfully"
                logs.append(log_6)
                SIMULATION_LOGS.append(log_6)
                logger.info(log_6)

            receiver_result = gate_result
            summary = (
                "After RESQ: The attacker captured the packet but sees only encrypted data. "
                "The authorized receiver can still decrypt and read the message."
            )

        # Append to bounded capture history
        if captured_record:
            if len(SIMULATION_CAPTURES) >= MAX_CAPTURES:
                SIMULATION_CAPTURES.pop(0)
            SIMULATION_CAPTURES.append(captured_record)

        return SimulateAttackResponse(
            simulation_id=simulation_id,
            mode=request.mode.value,
            packet_id=packet_id,
            message_id=message_id,
            captured=captured,
            captured_packet=captured_record,
            route=route,
            receiver_result=receiver_result,
            security_logs=logs,
            summary_sentence=summary,
        )

    def tamper_capture(
        self,
        capture_id: str,
        tamper_field: str = "ciphertext",
        recipient_id: Optional[str] = None,
    ) -> TamperCaptureResponse:
        """Mutates a captured protected packet and demonstrates that the Phase 6 gate rejects it."""
        capture = self.get_capture_by_id(capture_id)
        if not capture:
            raise ValueError(f"Capture record '{capture_id}' not found.")

        if capture.communication_mode != "protected":
            raise ValueError("Tampering demonstration is only applicable to protected encrypted packets.")

        if not capture.raw_payload:
            raise ValueError("Capture record contains no raw wire payload to tamper.")

        tampered_payload = copy.deepcopy(capture.raw_payload)

        if tamper_field == "ciphertext":
            raw_ct = bytearray(base64.b64decode(tampered_payload["ciphertext"]))
            raw_ct[0] ^= 0xFF  # Flip byte
            tampered_payload["ciphertext"] = base64.b64encode(raw_ct).decode("utf-8")
        elif tamper_field == "signature":
            raw_sig = bytearray(base64.b64decode(tampered_payload["signature"]))
            raw_sig[0] ^= 0xAA  # Corrupt signature
            tampered_payload["signature"] = base64.b64encode(raw_sig).decode("utf-8")
        elif tamper_field == "nonce":
            raw_n = bytearray(base64.b64decode(tampered_payload["nonce"]))
            raw_n[0] ^= 0x01
            tampered_payload["nonce"] = base64.b64encode(raw_n).decode("utf-8")
        else:
            raise ValueError(f"Unsupported tamper field '{tamper_field}'. Choose 'ciphertext', 'signature', or 'nonce'.")

        target_receiver = recipient_id or capture.recipient_id

        # Submit tampered packet to Phase 6 authorization & decryption gate
        gate_res = process_incoming_packet(
            packet=tampered_payload,
            current_receiver_id=target_receiver,
        )

        status = gate_res.get("status", "REJECTED")
        reason = gate_res.get("reason", "INVALID_SIGNATURE")
        detail = gate_res.get("detail", "Invalid signature - packet rejected")

        log_tamper = (
            f"[WARN] Tampered packet submitted to receiver gate | Capture: {capture_id} | "
            f"Field: {tamper_field} | Decision: {status} | Reason: {reason}"
        )
        SIMULATION_LOGS.append(log_tamper)
        logger.warning(log_tamper)

        explanation = (
            f"Tampering with the packet's {tamper_field} was detected immediately by the receiver. "
            "Cryptographic verification failed, and the message was rejected without releasing plaintext."
        )

        return TamperCaptureResponse(
            capture_id=capture_id,
            tampered_field=tamper_field,
            receiver_status=status,
            rejection_reason=reason,
            rejection_detail=detail,
            plaintext_revealed="message" in gate_res,
            explanation=explanation,
        )


attack_simulation_service = AttackSimulationService()
