from pathlib import Path
import sys
import unittest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app
from backend.app.core.mesh_node import MeshNode
from backend.app.models.registry import RegisterMemberRequest
from backend.app.services.attack_simulation_service import attack_simulation_service
from backend.app.services.crypto_service import crypto_service
from backend.app.services.dashboard_service import dashboard_service
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.message_service import message_service
from backend.app.services.registry_service import registry_service
from backend.app.storage.json_store import save_json


class TestPhase8Dashboard(unittest.TestCase):
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
        dashboard_service.registry_service = registry_service
        dashboard_service.message_service = message_service

        reset_network()
        attack_simulation_service.reset_simulation()

        # Seed 3 nodes
        self.sender = self._register_member("Alice", "Alpha")
        self.receiver = self._register_member("Bob", "Beta")
        self.attacker = self._register_member("Eve", "Gamma")

        net = get_network()
        net.add_node(MeshNode(self.sender.device_id))
        net.add_node(MeshNode(self.attacker.device_id, is_attacker=True))
        net.add_node(MeshNode(self.receiver.device_id))
        net.connect_nodes(self.sender.device_id, self.attacker.device_id)
        net.connect_nodes(self.attacker.device_id, self.receiver.device_id)

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

    def test_1_dashboard_overview_telemetry(self):
        """Verifies GET /api/dashboard/overview aggregates truthful live system metrics."""
        resp = self.client.get("/api/dashboard/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["phase"], 8)
        self.assertTrue(data["blackout_in_effect"])

        # Check operational status pills
        ops = data["operational_status"]
        self.assertEqual(ops["cellular_status"], "offline")
        self.assertEqual(ops["mesh_status"], "active")
        self.assertEqual(ops["encryption_status"], "active")
        self.assertEqual(ops["identity_status"], "verified")
        self.assertEqual(ops["decryption_status"], "enforced")

        # Check nodes
        self.assertEqual(len(data["nodes"]), 3)
        node_ids = {n["node_id"] for n in data["nodes"]}
        self.assertIn(self.sender.device_id, node_ids)
        self.assertIn(self.receiver.device_id, node_ids)

        # Check attacker node
        self.assertTrue(data["attacker"]["is_sniffing"])
        self.assertEqual(data["attacker"]["attacker_node_id"], self.attacker.device_id)

        # Check summary takeaway
        self.assertIn("The goal is not to prevent packet capture", data["summary_takeaway"])

    def test_2_dashboard_quick_dispatch_protected(self):
        """Verifies POST /api/dashboard/quick-dispatch executes end-to-end protected dispatch."""
        req_payload = {
            "mode": "protected",
            "sender_id": self.sender.rescue_id,
            "recipient_id": self.receiver.rescue_id,
            "message": "CRITICAL: Sector 4 search ongoing. Team Alpha in position.",
        }
        resp = self.client.post("/api/dashboard/quick-dispatch", json=req_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "DISPATCHED")
        self.assertEqual(data["mode"], "protected")
        self.assertTrue(data["captured_by_attacker"])
        self.assertFalse(data["attacker_readable"])
        self.assertIn("encrypted", data["attacker_sniffed"])
        self.assertEqual(data["security_gate_decision"], "AUTHORIZED_DECRYPTED")
        self.assertEqual(data["decrypted_message"], req_payload["message"])
        self.assertIsNotNone(data["overview"])

    def test_3_dashboard_quick_dispatch_vulnerable(self):
        """Verifies POST /api/dashboard/quick-dispatch executes vulnerable unencrypted dispatch."""
        req_payload = {
            "mode": "vulnerable",
            "sender_id": self.sender.rescue_id,
            "recipient_id": self.receiver.rescue_id,
            "message": "UNENCRYPTED DISPATCH: Medical supplies requested at outpost 2.",
        }
        resp = self.client.post("/api/dashboard/quick-dispatch", json=req_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["mode"], "vulnerable")
        self.assertTrue(data["captured_by_attacker"])
        self.assertTrue(data["attacker_readable"])
        self.assertIn("Medical supplies requested", data["attacker_sniffed"])

    def test_4_dashboard_metrics_truthfulness(self):
        """Verifies metrics update dynamically after dispatch."""
        before_resp = self.client.get("/api/dashboard/overview").json()
        initial_captures = before_resp["attacker"]["total_intercepted"]

        # Send a dispatch
        self.client.post("/api/dashboard/quick-dispatch", json={
            "mode": "protected",
            "sender_id": self.sender.rescue_id,
            "recipient_id": self.receiver.rescue_id,
            "message": "Telemetry verification message",
        })

        after_resp = self.client.get("/api/dashboard/overview").json()
        self.assertEqual(after_resp["attacker"]["total_intercepted"], initial_captures + 1)
        self.assertIsNotNone(after_resp["active_route"])
        self.assertEqual(after_resp["active_route"]["source"], self.sender.device_id)


if __name__ == "__main__":
    unittest.main()
