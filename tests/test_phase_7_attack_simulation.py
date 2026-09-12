import base64
from pathlib import Path
import sys
import unittest
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.core.mesh_node import MeshNode
from backend.app.models.attack import SimulateAttackRequest, SimulationMode
from backend.app.models.registry import MemberStatus, RegisterMemberRequest
from backend.app.services.attack_simulation_service import attack_simulation_service
from backend.app.services.crypto_service import crypto_service
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.message_service import message_service
from backend.app.services.registry_service import registry_service
from backend.app.storage.json_store import save_json


class TestPhase7AttackSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        import tempfile
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir_obj.name)
        self.registry_path = self.test_dir / "test_registry.json"
        self.keys_dir = self.test_dir / "keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True)

        save_json(self.registry_path, {"version": 1, "members": []})

        self.orig_reg_path = registry_service.registry_path
        self.orig_keys_dir = crypto_service.keys_dir

        registry_service.registry_path = self.registry_path
        crypto_service.keys_dir = self.keys_dir
        crypto_service.registry_service = registry_service
        message_service.registry_service = registry_service
        message_service.crypto_service = crypto_service
        attack_simulation_service.registry_service = registry_service
        attack_simulation_service.message_service = message_service

        reset_network()
        attack_simulation_service.reset_simulation()

        # Provision 3 active members: Sender, Recipient, Attacker
        self.sender = self._register_member("Alice", "Unit A")
        self.receiver = self._register_member("Bob", "Unit B")
        self.attacker_member = self._register_member("Eve", "Unknown")

        # Set up 3-node linear mesh topology: Sender <---> Attacker <---> Receiver
        net = get_network()
        net.add_node(MeshNode(self.sender.device_id))
        net.add_node(MeshNode(self.attacker_member.device_id, is_attacker=True))
        net.add_node(MeshNode(self.receiver.device_id))
        net.connect_nodes(self.sender.device_id, self.attacker_member.device_id)
        net.connect_nodes(self.attacker_member.device_id, self.receiver.device_id)

    def tearDown(self):
        registry_service.registry_path = self.orig_reg_path
        crypto_service.keys_dir = self.orig_keys_dir
        crypto_service.registry_service = registry_service
        message_service.registry_service = registry_service
        message_service.crypto_service = crypto_service
        reset_network()
        attack_simulation_service.reset_simulation()
        try:
            self.temp_dir_obj.cleanup()
        except Exception:
            pass

    def _register_member(self, name: str, team: str):
        req = RegisterMemberRequest(name=name, team=team, role="Responder")
        member = registry_service.register_member(req)
        crypto_service.initialize_device_keys(member.device_id)
        return registry_service.get_member_by_device_id(member.device_id)

    def test_1_vulnerable_mode_exposure(self):
        """Mode A (Vulnerable): Unencrypted packet is sniffed and attacker reads plaintext."""
        secret_msg = "VULNERABLE-CRITICAL: Three casualties trapped in sector 4."
        req = SimulateAttackRequest(
            mode=SimulationMode.VULNERABLE,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message=secret_msg,
            attacker_node_id=self.attacker_member.device_id,
        )

        resp = attack_simulation_service.simulate_attack(req)

        self.assertEqual(resp.mode, "vulnerable")
        self.assertTrue(resp.captured)
        self.assertIsNotNone(resp.captured_packet)

        cap = resp.captured_packet
        self.assertTrue(cap.contains_plaintext)
        self.assertTrue(cap.plaintext_exposed)
        self.assertTrue(cap.message_readable_by_attacker)
        self.assertFalse(cap.ciphertext_present)
        self.assertEqual(cap.security_result, "Message exposed")
        self.assertIn(secret_msg, cap.sniffed_content)
        self.assertEqual(resp.summary_sentence, "Before RESQ: The attacker captured the packet and read the emergency message.")

        # Test via REST API endpoint as well
        api_resp = self.client.post("/api/attack/simulate", json=req.model_dump())
        self.assertEqual(api_resp.status_code, 200)
        data = api_resp.json()
        self.assertEqual(data["mode"], "vulnerable")
        self.assertTrue(data["captured_packet"]["plaintext_exposed"])

    def test_2_protected_mode_confidentiality_and_zero_plaintext(self):
        """Mode B (Protected): Ciphertext captured, attacker CANNOT read plaintext, zero plaintext in capture."""
        secret_msg = "CONFIDENTIAL: Alpha team coordinates are 27.33, 88.61."
        req = SimulateAttackRequest(
            mode=SimulationMode.PROTECTED,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message=secret_msg,
            attacker_node_id=self.attacker_member.device_id,
        )

        resp = attack_simulation_service.simulate_attack(req)

        self.assertEqual(resp.mode, "protected")
        self.assertTrue(resp.captured)
        self.assertIsNotNone(resp.captured_packet)

        cap = resp.captured_packet
        self.assertFalse(cap.contains_plaintext)
        self.assertFalse(cap.plaintext_exposed)
        self.assertFalse(cap.message_readable_by_attacker)
        self.assertTrue(cap.ciphertext_present)
        self.assertTrue(cap.signature_present)
        self.assertEqual(cap.security_result, "Plaintext protected")
        self.assertNotIn(secret_msg, cap.sniffed_content)
        self.assertIn("encrypted", cap.sniffed_content)

        # Recursive check: assert secret_msg is absent from the entire capture object
        raw_cap_str = str(cap.model_dump())
        self.assertNotIn(secret_msg, raw_cap_str)

        # Verify summary message
        self.assertIn("After RESQ: The attacker captured the packet but sees only encrypted data", resp.summary_sentence)

    def test_3_attacker_has_no_secret_keys(self):
        """Attacker node and capture structures never contain private keys or shared secrets."""
        req = SimulateAttackRequest(
            mode=SimulationMode.PROTECTED,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Secret mission telemetry",
            attacker_node_id=self.attacker_member.device_id,
        )
        resp = attack_simulation_service.simulate_attack(req)
        cap = resp.captured_packet

        # Verify no sensitive key material in capture record
        cap_dict = cap.model_dump()
        forbidden_keys = [
            "private_key",
            "signing_private_key",
            "encryption_private_key",
            "shared_secret",
            "decryption_key",
        ]
        for f_key in forbidden_keys:
            self.assertNotIn(f_key, cap_dict)
            if cap.raw_payload:
                self.assertNotIn(f_key, cap.raw_payload)

    def test_4_authorized_receiver_still_decrypts(self):
        """In protected mode, the authorized recipient successfully verifies and decrypts via Phase 6."""
        secret_msg = "Emergency medical supplies arriving at LZ 1."
        req = SimulateAttackRequest(
            mode=SimulationMode.PROTECTED,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message=secret_msg,
            attacker_node_id=self.attacker_member.device_id,
        )
        resp = attack_simulation_service.simulate_attack(req)

        self.assertEqual(resp.receiver_result.get("status"), "SUCCESS")
        self.assertEqual(resp.receiver_result.get("message"), secret_msg)
        self.assertEqual(resp.receiver_result.get("sender_id"), self.sender.rescue_id)

    def test_5_tampered_captured_packet_rejected(self):
        """Mutating captured ciphertext causes Phase 6 receiver verification to reject it."""
        req = SimulateAttackRequest(
            mode=SimulationMode.PROTECTED,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Tamper defense validation message.",
            attacker_node_id=self.attacker_member.device_id,
        )
        resp = attack_simulation_service.simulate_attack(req)
        capture_id = resp.captured_packet.capture_id

        # Tamper via endpoint / service
        tamper_res = attack_simulation_service.tamper_capture(
            capture_id=capture_id,
            tamper_field="ciphertext",
            recipient_id=self.receiver.device_id,
        )

        self.assertEqual(tamper_res.receiver_status, "REJECTED")
        self.assertIn(tamper_res.rejection_reason, ["INVALID_SIGNATURE", "DECRYPTION_FAILED"])
        self.assertFalse(tamper_res.plaintext_revealed)

        # Test API endpoint
        api_tamper = self.client.post(
            f"/api/attack/captures/{capture_id}/tamper",
            json={"capture_id": capture_id, "tamper_field": "signature"},
        )
        self.assertEqual(api_tamper.status_code, 200)
        self.assertEqual(api_tamper.json()["receiver_status"], "REJECTED")

    def test_6_multi_hop_capture(self):
        """Packet traversing 3+ nodes is captured by sniffer without leaking plaintext."""
        net = get_network()
        relay1 = "RELAY-NODE-01"
        relay2 = "RELAY-NODE-02"
        net.add_node(MeshNode(relay1))
        net.add_node(MeshNode(relay2))

        # Reconnect: Sender -> Relay1 -> Attacker -> Relay2 -> Receiver
        net.disconnect_nodes(self.sender.device_id, self.attacker_member.device_id)
        net.disconnect_nodes(self.attacker_member.device_id, self.receiver.device_id)

        net.connect_nodes(self.sender.device_id, relay1)
        net.connect_nodes(relay1, self.attacker_member.device_id)
        net.connect_nodes(self.attacker_member.device_id, relay2)
        net.connect_nodes(relay2, self.receiver.device_id)

        req = SimulateAttackRequest(
            mode=SimulationMode.PROTECTED,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Multi-hop confidential payload",
            attacker_node_id=self.attacker_member.device_id,
        )
        resp = attack_simulation_service.simulate_attack(req)

        self.assertTrue(resp.captured)
        self.assertGreaterEqual(len(resp.route), 4)
        self.assertEqual(resp.captured_packet.security_result, "Plaintext protected")
        self.assertEqual(resp.receiver_result.get("status"), "SUCCESS")
        self.assertEqual(resp.receiver_result.get("message"), "Multi-hop confidential payload")

    def test_7_simulation_reset_isolation(self):
        """Reset clears Phase 7 simulation state, while preserving registry, keys, and network."""
        req = SimulateAttackRequest(
            mode=SimulationMode.VULNERABLE,
            sender_id=self.sender.rescue_id,
            recipient_id=self.receiver.rescue_id,
            message="Temporary reset message",
        )
        attack_simulation_service.simulate_attack(req)
        self.assertGreaterEqual(len(attack_simulation_service.list_captures()), 1)

        # Call reset
        reset_res = attack_simulation_service.reset_simulation()
        self.assertEqual(reset_res["status"], "RESET_SUCCESS")
        self.assertEqual(len(attack_simulation_service.list_captures()), 0)

        # Check that registry members and keypairs still exist
        m1 = registry_service.get_member_by_device_id(self.sender.device_id)
        self.assertIsNotNone(m1)
        self.assertEqual(m1.name, "Alice")
        key = crypto_service.load_device_signing_private_key(self.sender.device_id)
        self.assertIsNotNone(key)


if __name__ == "__main__":
    unittest.main()
