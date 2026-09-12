"""Phase 6 Authorization & Controlled Decryption Gate Test Suite.

Verifies end-to-end integration across Phases 1-6:
1. Valid message end-to-end (Real Phase 5 pipeline -> Phase 6 gate -> Plaintext)
2. Tampered ciphertext rejection (Signature verification / AEAD tag failure)
3. Tampered sender ID rejection
4. Unknown sender rejection
5. Revoked sender rejection
6. Unauthorized recipient rejection
7. Wrong decryption key rejection
8. Tampered nonce rejection
9. Tampered salt rejection
10. Tampered ephemeral public key rejection
11. Protocol-level replay protection (duplicate packet_id and expired timestamp)
12. Multi-hop mesh inbox pipeline & REST API endpoints
13. Protocol contract verification (HKDF-SHA256, ChaCha20-Poly1305, Ed25519 canonical JSON)
"""

import base64
import json
import os
import shutil
import sys
import time
from pathlib import Path
import unittest
import pytest
from fastapi.testclient import TestClient

from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives import serialization

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.core.crypto import (
    canonicalize_payload,
    decrypt_authenticated,
    verify_signature,
)
from backend.app.core.decryption_gate import (
    process_incoming_packet,
    clear_replay_cache,
    SECURITY_LOGS,
)
from backend.app.core.mesh_node import MeshNode
from backend.app.models.crypto import EncryptionEnvelope
from backend.app.models.registry import MemberStatus, RegisterMemberRequest, RescueMember
from backend.app.services.crypto_service import crypto_service
from backend.app.services.message_service import message_service
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.registry_service import registry_service
from backend.app.storage.json_store import save_json


class TestPhase6DecryptionGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        """Set up an isolated temporary registry, keys directory, and mesh network."""
        import tempfile
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir_obj.name)
        self.registry_path = self.test_dir / "test_registry.json"
        self.keys_dir = self.test_dir / "keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        save_json(self.registry_path, {"version": 1, "members": []})

        # Save original service configurations
        self.orig_reg_path = registry_service.registry_path
        self.orig_keys_dir = crypto_service.keys_dir

        # Point singletons to isolated test environment
        registry_service.registry_path = self.registry_path
        crypto_service.keys_dir = self.keys_dir
        crypto_service.registry_service = registry_service
        message_service.registry_service = registry_service
        message_service.crypto_service = crypto_service

        reset_network()
        clear_replay_cache()
        SECURITY_LOGS.clear()

        # Seed 4 real members with active keys
        self.sender = self._register_and_init("Alice Alpha", "Team 1", MemberStatus.ACTIVE)
        self.receiver = self._register_and_init("Bob Bravo", "Team 1", MemberStatus.ACTIVE)
        self.revoked = self._register_and_init("Charlie Charlie", "Team 2", MemberStatus.REVOKED)
        self.third_party = self._register_and_init("David Delta", "Team 2", MemberStatus.ACTIVE)

        # Connect sender and receiver nodes in the mesh network
        net = get_network()
        net.add_node(MeshNode(self.sender.device_id))
        net.add_node(MeshNode(self.receiver.device_id))
        net.connect_nodes(self.sender.device_id, self.receiver.device_id)

    def tearDown(self):
        """Restore services and clean up temporary test files."""
        registry_service.registry_path = self.orig_reg_path
        crypto_service.keys_dir = self.orig_keys_dir
        crypto_service.registry_service = registry_service
        message_service.registry_service = registry_service
        message_service.crypto_service = crypto_service
        reset_network()
        clear_replay_cache()
        try:
            self.temp_dir_obj.cleanup()
        except Exception:
            pass


    def _register_and_init(self, name: str, team: str, status: MemberStatus) -> RescueMember:
        req = RegisterMemberRequest(name=name, team=team, role="Responder")
        member = registry_service.register_member(req)
        crypto_service.initialize_device_keys(member.device_id)
        if status == MemberStatus.REVOKED:
            registry_service.revoke_member(member.rescue_id)
        return registry_service.get_member_by_device_id(member.device_id)


    # =========================================================================
    # THE 11 SECURITY SCENARIOS + API & CONTRACT VERIFICATION
    # =========================================================================

    def test_1_valid_message_end_to_end(self):
        """Test 1: Registered + active + valid signature + authorized recipient -> SUCCESS & Plaintext released."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="CRITICAL: Evacuation at sector 4 required immediately.",
        )
        packet_dict = send_resp.payload.model_dump()

        # Phase 6 gate processing
        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["message"], "CRITICAL: Evacuation at sector 4 required immediately.")
        self.assertEqual(result["sender_name"], self.sender.name)
        self.assertEqual(result["sender_id"], self.sender.rescue_id)
        self.assertTrue(any(log["event"] == "MESSAGE_DECRYPTED" for log in SECURITY_LOGS))

    def test_2_tampered_ciphertext_rejection(self):
        """Test 2: Attacker tampers with ciphertext -> REJECTED, no plaintext released."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Secure evacuation coordinates: 27.33, 88.61",
        )
        packet_dict = send_resp.payload.model_dump()

        # Tamper with the ciphertext bytes
        ct_raw = bytearray(base64.b64decode(packet_dict["ciphertext"]))
        ct_raw[0] ^= 0xFF
        packet_dict["ciphertext"] = base64.b64encode(ct_raw).decode("utf-8")

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertIn(result["reason"], ["INVALID_SIGNATURE", "DECRYPTION_FAILED"])
        self.assertNotIn("message", result)

    def test_3_tampered_sender_id_rejection(self):
        """Test 3: Attacker tampers with sender ID -> REJECTED, no plaintext released."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Supply drop scheduled",
        )
        packet_dict = send_resp.payload.model_dump()

        # Tamper with sender_rescue_id to spoof third party
        packet_dict["sender_rescue_id"] = self.third_party.rescue_id

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")
        self.assertNotIn("message", result)

    def test_4_unknown_sender_rejection(self):
        """Test 4: Unknown sender not in registry -> REJECTED at Gate Check 1."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Ghost message",
        )
        packet_dict = send_resp.payload.model_dump()
        packet_dict["sender_rescue_id"] = "RESQ-999"
        packet_dict["sender_device_id"] = "DEVICE-999"

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "UNKNOWN_SENDER")
        self.assertNotIn("message", result)


    def test_5_revoked_sender_rejection(self):
        """Test 5: Revoked sender -> REJECTED at Gate Check 2."""
        # Charlie is revoked
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Valid before revocation",
        )
        packet_dict = send_resp.payload.model_dump()
        # Set sender to revoked Charlie
        packet_dict["sender_rescue_id"] = self.revoked.rescue_id
        packet_dict["sender_device_id"] = self.revoked.device_id

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "SENDER_REVOKED")
        self.assertNotIn("message", result)

    def test_6_unauthorized_recipient_rejection(self):
        """Test 6: Packet destined for Bob, but David attempts to decrypt it -> REJECTED at Gate Check 4."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Confidential rescue blueprint",
        )
        packet_dict = send_resp.payload.model_dump()

        # David Delta (RESQ-004) attempts to process Bob's packet
        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.third_party.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "UNAUTHORIZED_RECIPIENT")
        self.assertNotIn("message", result)

    def test_7_wrong_decryption_key_rejection(self):
        """Test 7: Authorized recipient ID, but wrong X25519 private key passed -> REJECTED at Gate Check 6."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Encrypted medical telemetry",
        )
        packet_dict = send_resp.payload.model_dump()

        # Pass a freshly generated, unrelated private key
        wrong_key = x25519.X25519PrivateKey.generate()

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            receiver_private_key=wrong_key,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "DECRYPTION_FAILED")
        self.assertNotIn("message", result)

    def test_8_tampered_nonce_rejection(self):
        """Test 8: Attacker tampers with nonce -> REJECTED at Gate Check 3 (signature failure)."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Nonce tamper test",
        )
        packet_dict = send_resp.payload.model_dump()

        nonce_raw = bytearray(base64.b64decode(packet_dict["nonce"]))
        nonce_raw[0] ^= 0x01
        packet_dict["nonce"] = base64.b64encode(nonce_raw).decode("utf-8")

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")
        self.assertNotIn("message", result)

    def test_9_tampered_salt_rejection(self):
        """Test 9: Attacker tampers with HKDF salt -> REJECTED at Gate Check 3 (signature failure)."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Salt tamper test",
        )
        packet_dict = send_resp.payload.model_dump()

        salt_raw = bytearray(base64.b64decode(packet_dict["salt"]))
        salt_raw[0] ^= 0x01
        packet_dict["salt"] = base64.b64encode(salt_raw).decode("utf-8")

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")
        self.assertNotIn("message", result)

    def test_10_tampered_ephemeral_key_rejection(self):
        """Test 10: Attacker tampers with ephemeral public key -> REJECTED at Gate Check 3."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Ephemeral key tamper test",
        )
        packet_dict = send_resp.payload.model_dump()

        ephem_raw = bytearray(base64.b64decode(packet_dict["ephemeral_public_key"]))
        ephem_raw[0] ^= 0x01
        packet_dict["ephemeral_public_key"] = base64.b64encode(ephem_raw).decode("utf-8")

        result = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )

        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")
        self.assertNotIn("message", result)

    def test_11_replay_attack_and_drift_rejection(self):
        """Test 11: Replaying an accepted packet or sending expired timestamp is REJECTED."""
        send_resp = message_service.send_secure_message(
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="One-time authorization token",
        )
        packet_dict = send_resp.payload.model_dump()

        # First delivery -> SUCCESS
        res1 = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["message"], "One-time authorization token")

        # Second delivery (replay attack) -> REJECTED
        res2 = process_incoming_packet(
            packet=packet_dict,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )
        self.assertEqual(res2["status"], "REJECTED")
        self.assertEqual(res2["reason"], "REPLAY_ATTACK_DETECTED")
        self.assertNotIn("message", res2)

        # Expired timestamp check (> 300 seconds old)
        clear_replay_cache()
        expired_packet = dict(packet_dict)
        expired_packet["packet_id"] = "PKT-EXPIRED-TEST"
        expired_packet["message_id"] = "MSG-EXPIRED-TEST"
        expired_packet["timestamp"] = int(time.time()) - 600

        res3 = process_incoming_packet(
            packet=expired_packet,
            current_receiver_id=self.receiver.rescue_id,
            registry_path=str(self.registry_path),
        )
        self.assertEqual(res3["status"], "REJECTED")
        self.assertIn(res3["reason"], ["TIMESTAMP_EXPIRED", "INVALID_SIGNATURE"])

    def test_12_multi_hop_mesh_inbox_and_rest_api(self):
        """Test 12: Multi-hop mesh inbox delivery + REST API endpoints (GET inbox, POST decrypt)."""
        net = get_network()
        # Add Relay Node
        relay_device_id = "DEVICE-RELAY"
        net.add_node(MeshNode(relay_device_id))
        # Disconnect direct link and force path: Sender -> Relay -> Receiver
        net.disconnect_nodes(self.sender.device_id, self.receiver.device_id)
        net.connect_nodes(self.sender.device_id, relay_device_id)
        net.connect_nodes(relay_device_id, self.receiver.device_id)

        # 1. Send via REST API
        send_req_data = {
            "sender_id": self.sender.rescue_id,
            "recipient_id": self.receiver.rescue_id,
            "message": "Relayed emergency distress dispatch",
        }
        api_resp = self.client.post("/api/messages/send", json=send_req_data)
        self.assertEqual(api_resp.status_code, 200)
        send_data = api_resp.json()
        packet_id = send_data["packet_id"]
        hops = len(send_data.get("hop_log", []))
        self.assertGreaterEqual(hops, 2)  # Traversed through relay

        # 2. Query Recipient Inbox via REST API
        inbox_resp = self.client.get(f"/api/messages/inbox/{self.receiver.rescue_id}")
        self.assertEqual(inbox_resp.status_code, 200)
        inbox_data = inbox_resp.json()
        self.assertGreaterEqual(len(inbox_data), 1)
        target_inbox_msg = next((m for m in inbox_data if m["packet_id"] == packet_id), None)
        self.assertIsNotNone(target_inbox_msg)
        self.assertEqual(target_inbox_msg["sender_rescue_id"], self.sender.rescue_id)
        self.assertEqual(target_inbox_msg["recipient_rescue_id"], self.receiver.rescue_id)

        # 3. Decrypt via REST API as Bob (Authorized)
        decrypt_req = {
            "recipient_id": self.receiver.rescue_id,
            "packet_id": packet_id,
        }
        dec_resp = self.client.post("/api/messages/decrypt", json=decrypt_req)
        self.assertEqual(dec_resp.status_code, 200)
        dec_data = dec_resp.json()
        self.assertEqual(dec_data["status"], "SUCCESS")
        self.assertEqual(dec_data["message"], "Relayed emergency distress dispatch")
        self.assertEqual(dec_data["sender_id"], self.sender.rescue_id)

        # 4. Attempt Decrypt as Unauthorized David Delta via direct payload -> REJECTED
        unauth_decrypt_req = {
            "recipient_id": self.third_party.rescue_id,
            "payload": send_data["payload"],
        }
        unauth_resp = self.client.post("/api/messages/decrypt", json=unauth_decrypt_req)
        self.assertEqual(unauth_resp.status_code, 200)
        unauth_data = unauth_resp.json()
        self.assertEqual(unauth_data["status"], "REJECTED")
        self.assertEqual(unauth_data["reason"], "UNAUTHORIZED_RECIPIENT")
        self.assertIsNone(unauth_data.get("message"))


    def test_13_protocol_contract_mathematical_compatibility(self):
        """Test 13: Strict contract test proving Phase 5 output is bit-for-bit compatible with Phase 6 input."""
        from backend.app.core.crypto import (
            decode_x25519_public_key_b64,
            decode_ed25519_public_key_b64,
            encrypt_authenticated,
            sign_bytes,
        )
        from backend.app.models.messages import SecureMessagePayload

        recipient_member = registry_service.get_member_by_device_id(self.receiver.device_id)
        sender_member = registry_service.get_member_by_device_id(self.sender.device_id)
        recipient_pub = decode_x25519_public_key_b64(recipient_member.encryption_public_key)
        sender_sign_priv = crypto_service.load_device_signing_private_key(self.sender.device_id)

        # 1. Phase 5 authenticated encryption: Ephemeral X25519 + HKDF-SHA256 + ChaCha20-Poly1305 with AAD
        envelope = encrypt_authenticated(
            recipient_public_key=recipient_pub,
            plaintext=b"Protocol contract payload test",
        )

        packet_id = "PKT-CONTRACT-001"
        message_id = "MSG-CONTRACT-001"
        timestamp = int(time.time())

        # 2. Canonical JSON dictionary & Ed25519 digital signature
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
        signature = sign_bytes(sender_sign_priv, canonical_bytes)

        signed_payload = SecureMessagePayload(
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
            signature=signature,
        )

        # 3. Verify all fields are valid Base64 wire encodings
        self.assertEqual(len(base64.b64decode(signed_payload.salt)), 16)
        self.assertEqual(len(base64.b64decode(signed_payload.nonce)), 12)
        self.assertEqual(len(base64.b64decode(signed_payload.ephemeral_public_key)), 32)
        self.assertEqual(len(base64.b64decode(signed_payload.signature)), 64)
        raw_ciphertext = base64.b64decode(signed_payload.ciphertext)
        self.assertGreater(len(raw_ciphertext), 16)

        # 4. Verify signature independently over RFC 8785 canonical bytes
        sender_pub_key = decode_ed25519_public_key_b64(sender_member.signing_public_key)
        self.assertTrue(verify_signature(sender_pub_key, canonical_bytes, signed_payload.signature))

        # 5. Feed directly into Phase 6 process_incoming_packet
        gate_res = process_incoming_packet(
            packet=signed_payload,
            current_receiver_id=self.receiver.device_id,
            registry_path=str(self.registry_path),
        )
        self.assertEqual(gate_res["status"], "SUCCESS")
        self.assertEqual(gate_res["message"], "Protocol contract payload test")



if __name__ == "__main__":
    unittest.main()