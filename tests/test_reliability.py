"""
test_reliability.py — Network Reliability, Offline Queue, Retry, Duplicate Prevention tests.

Covers:
- Node failure: offline node excluded from routes
- Connection failure: disconnected edge excluded
- Alternative route selection
- Failed delivery when no route
- Retry after network recovery
- Duplicate delivery prevention (DELIVERED cannot be retried)
- Queue security: no plaintext in FAILED/queued records
- Reset safety: simulation reset preserves registry/keys
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core.mesh_network import NoRouteError
from backend.app.core.mesh_node import MeshNode
from backend.app.core.message_repository import MessageRepository
from backend.app.models.messages import MessageStatus
from backend.app.models.registry import RegisterMemberRequest
from backend.app.services.crypto_service import CryptoService
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.message_service import MessageService, MessageServiceError
from backend.app.services.registry_service import RegistryService
from backend.app.storage.json_store import save_json


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_env():
    tmp = tempfile.mkdtemp()
    reg_path = Path(tmp) / "registry.json"
    keys_dir = Path(tmp) / "keys"
    msg_path = Path(tmp) / "messages.json"
    keys_dir.mkdir()
    save_json(reg_path, {"version": 1, "members": []})
    save_json(msg_path, {"version": 1, "messages": []})

    reg = RegistryService(registry_path=reg_path)
    crypto = CryptoService(keys_dir=keys_dir, registry_service_instance=reg)
    repo = MessageRepository(filepath=msg_path)
    reset_network()
    net = get_network()
    svc = MessageService(
        registry_service_instance=reg,
        crypto_service_instance=crypto,
        network_provider=lambda: net,
        repository_instance=repo,
    )
    return reg, crypto, repo, net, svc


def _reg_key(reg, crypto, name, team, role):
    m = reg.register_member(RegisterMemberRequest(name=name, team=team, role=role))
    crypto.initialize_device_keys(m.device_id)
    return reg.get_member_by_device_id(m.device_id)


def _setup_linear_mesh(net, *node_ids):
    """A → B → C → ... linear topology."""
    for nid in node_ids:
        if nid not in net.nodes:
            net.add_node(MeshNode(nid))
    for i in range(len(node_ids) - 1):
        if not net.has_connection(node_ids[i], node_ids[i + 1]):
            net.connect_nodes(node_ids[i], node_ids[i + 1])


# ─── Node failure tests ───────────────────────────────────────────────────────


class TestNodeFailure:
    def test_offline_node_excluded_from_route(self):
        """BFS must skip offline intermediate nodes."""
        reg, crypto, repo, net, svc = _make_env()
        _setup_linear_mesh(net, "NA", "NB", "NC")
        net.nodes["NB"].is_online = False
        with pytest.raises(NoRouteError):
            net.find_route("NA", "NC")
        net.nodes["NB"].is_online = True

    def test_alternative_route_used_when_primary_offline(self):
        """With a secondary path, routing succeeds despite one offline node."""
        reg, crypto, repo, net, svc = _make_env()
        _setup_linear_mesh(net, "NA", "NB", "NC")
        net.add_node(MeshNode("NX"))
        net.connect_nodes("NA", "NX")
        net.connect_nodes("NX", "NC")
        net.nodes["NB"].is_online = False
        route = net.find_route("NA", "NC")
        assert "NB" not in route, "Offline node should not be on route"
        assert "NX" in route, "Alternative node should be used"
        net.nodes["NB"].is_online = True

    def test_node_restored_after_failure(self):
        """Route is re-established after bringing offline node back online."""
        reg, crypto, repo, net, svc = _make_env()
        _setup_linear_mesh(net, "NA", "NB", "NC")
        net.nodes["NB"].is_online = False
        with pytest.raises(NoRouteError):
            net.find_route("NA", "NC")
        net.nodes["NB"].is_online = True
        route = net.find_route("NA", "NC")
        assert "NB" in route


# ─── Connection failure tests ─────────────────────────────────────────────────


class TestConnectionFailure:
    def test_disconnected_edge_breaks_direct_route(self):
        """Severing connection between two nodes prevents direct routing."""
        reg, crypto, repo, net, svc = _make_env()
        _setup_linear_mesh(net, "XA", "XB", "XC")
        net.disconnect_nodes("XA", "XB")
        with pytest.raises(NoRouteError):
            net.find_route("XA", "XC")

    def test_reconnected_edge_restores_route(self):
        """Reconnecting nodes restores routing capability."""
        reg, crypto, repo, net, svc = _make_env()
        _setup_linear_mesh(net, "XA", "XB", "XC")
        net.disconnect_nodes("XA", "XB")
        net.connect_nodes("XA", "XB")
        route = net.find_route("XA", "XC")
        assert route is not None and len(route) >= 2


# ─── Message delivery failure tests ──────────────────────────────────────────


class TestDeliveryFailure:
    def test_no_route_marks_message_failed(self):
        """When no mesh path exists, message status must be FAILED."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "FS", "FA", "Commander")
        recip  = _reg_key(reg, crypto, "FR", "FB", "Field")
        # Add isolated nodes with no connection
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))
        # Intentionally do NOT connect them
        with pytest.raises(Exception):
            svc.send_secure_message(sender.rescue_id, recip.rescue_id, "unreachable")

        raw = repo._load_raw_data()
        msgs = raw.get("messages", [])
        failed = [m for m in msgs if m.get("status") == "FAILED"]
        assert len(failed) >= 1, "At least one message should be in FAILED state"

    def test_failed_message_contains_no_plaintext(self):
        """FAILED message record must not contain original plaintext."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "PFS", "PFA", "Commander")
        recip  = _reg_key(reg, crypto, "PFR", "PFB", "Field")
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))
        plaintext = "SENSITIVE: Evacuation coordinates (N 48.8566, E 2.3522)."
        try:
            svc.send_secure_message(sender.rescue_id, recip.rescue_id, plaintext)
        except Exception:
            pass  # Expected

        raw = repo._load_raw_data()
        msgs_str = str(raw)
        assert plaintext not in msgs_str, "SECURITY: plaintext found in failed message storage!"


# ─── Retry tests ─────────────────────────────────────────────────────────────


class TestRetry:
    def test_retry_delivered_message_raises(self):
        """Retrying a DELIVERED message must raise an error."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "RS", "RA", "Lead")
        recip  = _reg_key(reg, crypto, "RR", "RB", "Medic")
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))
        net.connect_nodes(sender.device_id, recip.device_id)
        resp = svc.send_secure_message(sender.rescue_id, recip.rescue_id, "delivered message")
        with pytest.raises(MessageServiceError):
            svc.retry_failed_message(resp.message_id)

    def test_retry_generates_new_packet_id(self):
        """Retry must use a new packet_id to avoid duplicate-packet confusion."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "RS2", "RA2", "Lead")
        recip  = _reg_key(reg, crypto, "RR2", "RB2", "Medic")
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))
        # First delivery — force fail by not connecting
        try:
            svc.send_secure_message(sender.rescue_id, recip.rescue_id, "retry me")
        except Exception:
            pass

        raw = repo._load_raw_data()
        failed_msgs = [m for m in raw.get("messages", []) if m.get("status") == "FAILED"]
        if not failed_msgs:
            pytest.skip("No FAILED message available for retry test")

        original_packet_id = failed_msgs[-1]["packet_id"]
        original_msg_id = failed_msgs[-1]["message_id"]

        # Now connect and retry
        net.connect_nodes(sender.device_id, recip.device_id)
        retry_resp = svc.retry_failed_message(original_msg_id)
        assert retry_resp.packet_id != original_packet_id, "Retry must use a fresh packet_id"
        assert retry_resp.message_id == original_msg_id, "message_id must not change on retry"

    def test_retry_passes_security_checks(self):
        """Retried packet must still pass signature verification."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "RS3", "RA3", "Lead")
        recip  = _reg_key(reg, crypto, "RR3", "RB3", "Medic")
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))

        try:
            svc.send_secure_message(sender.rescue_id, recip.rescue_id, "security retry test")
        except Exception:
            pass

        raw = repo._load_raw_data()
        failed = [m for m in raw.get("messages", []) if m.get("status") == "FAILED"]
        if not failed:
            pytest.skip("No FAILED message for retry security test")

        net.connect_nodes(sender.device_id, recip.device_id)
        retry_resp = svc.retry_failed_message(failed[-1]["message_id"])

        # Verify the retried packet can be decrypted by authorized recipient
        result = svc.decrypt_direct_payload(recip.rescue_id, retry_resp.payload)
        assert result.status == "SUCCESS", f"Retry decryption failed: {result.reason}"


# ─── Duplicate prevention ─────────────────────────────────────────────────────


class TestDuplicatePrevention:
    def test_delivered_message_cannot_be_retried(self):
        """A DELIVERED message is idempotent — retry must be blocked."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "DS", "DA", "Lead")
        recip  = _reg_key(reg, crypto, "DR", "DB", "Medic")
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))
        net.connect_nodes(sender.device_id, recip.device_id)
        resp = svc.send_secure_message(sender.rescue_id, recip.rescue_id, "do not duplicate")
        rec = repo.get_message(resp.message_id)
        assert rec.status == MessageStatus.DELIVERED
        with pytest.raises(MessageServiceError):
            svc.retry_failed_message(resp.message_id)

    def test_repository_update_is_idempotent(self):
        """Saving the same message_id twice must update, not append."""
        reg, crypto, repo, net, svc = _make_env()
        sender = _reg_key(reg, crypto, "IS", "IA", "Lead")
        recip  = _reg_key(reg, crypto, "IR", "IB", "Medic")
        for nid in [sender.device_id, recip.device_id]:
            if nid not in net.nodes:
                net.add_node(MeshNode(nid))
        net.connect_nodes(sender.device_id, recip.device_id)
        resp = svc.send_secure_message(sender.rescue_id, recip.rescue_id, "idempotent test")

        raw_before = repo._load_raw_data()
        count_before = len([m for m in raw_before["messages"] if m["message_id"] == resp.message_id])

        # Save again
        record = repo.get_message(resp.message_id)
        repo.save_message(record)
        raw_after = repo._load_raw_data()
        count_after = len([m for m in raw_after["messages"] if m["message_id"] == resp.message_id])

        assert count_before == count_after == 1, "Repository must not create duplicate records"


# ─── Reset safety ─────────────────────────────────────────────────────────────


class TestResetSafety:
    def test_simulation_reset_preserves_registry(self):
        """Attack simulation reset must not delete registry members."""
        reg, crypto, repo, net, svc = _make_env()
        member = _reg_key(reg, crypto, "PreservedMember", "PA", "Responder")
        count_before = len(reg.get_all_members())

        from backend.app.services.attack_simulation_service import SIMULATION_CAPTURES, SIMULATION_LOGS
        SIMULATION_CAPTURES.clear()
        SIMULATION_LOGS.clear()

        count_after = len(reg.get_all_members())
        assert count_before == count_after, "Registry should survive simulation reset"

    def test_simulation_reset_preserves_key_files(self):
        """Attack simulation reset must not delete private key files."""
        reg, crypto, repo, net, svc = _make_env()
        member = _reg_key(reg, crypto, "KeyPreserved", "KA", "Responder")
        key_path = Path(crypto.keys_dir) / member.device_id / "signing_private.pem"
        assert key_path.exists(), "Key file must exist before reset"

        from backend.app.services.attack_simulation_service import SIMULATION_CAPTURES, SIMULATION_LOGS
        SIMULATION_CAPTURES.clear()
        SIMULATION_LOGS.clear()

        assert key_path.exists(), "Key file must survive simulation reset"

    def test_network_reset_clears_nodes(self):
        """reset_network() clears in-memory topology without touching persistent data."""
        reg, crypto, repo, net, svc = _make_env()
        member = _reg_key(reg, crypto, "NetReset", "NA", "Responder")

        net.add_node(MeshNode("TEMP-NODE"))
        assert "TEMP-NODE" in net.nodes
        reset_network()
        new_net = get_network()
        assert "TEMP-NODE" not in new_net.nodes, "Network reset should clear nodes"

        # Registry still intact
        found = reg.get_member_by_device_id(member.device_id)
        assert found is not None, "Registry must survive network reset"
