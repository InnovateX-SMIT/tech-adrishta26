from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from backend.app.core.decryption_gate import SECURITY_LOGS
from backend.app.models.attack import SimulateAttackRequest, SimulationMode
from backend.app.models.dashboard import (
    DashboardAttackerSummary,
    DashboardMessagingSummary,
    DashboardNodeSummary,
    DashboardOverviewResponse,
    DashboardRouteSummary,
    DashboardSecuritySummary,
    OperationalStatusPills,
    QuickDispatchRequest,
    QuickDispatchResponse,
)
from backend.app.models.messages import MessageStatus
from backend.app.models.registry import MemberStatus
from backend.app.services.attack_simulation_service import (
    SIMULATION_LOGS,
    attack_simulation_service,
)
from backend.app.services.mesh_service import get_network
from backend.app.services.message_service import message_service
from backend.app.services.registry_service import registry_service

logger = logging.getLogger("resq.dashboard")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DashboardService:
    def __init__(self) -> None:
        self.registry_service = registry_service
        self.message_service = message_service
        self.attack_service = attack_simulation_service

    def get_network(self):
        return get_network()

    def get_overview(self) -> DashboardOverviewResponse:
        net = self.get_network()
        all_members = self.registry_service.get_all_members()
        member_by_dev = {m.device_id: m for m in all_members}
        member_by_resq = {m.rescue_id: m for m in all_members}

        # Build node summaries
        node_summaries: List[DashboardNodeSummary] = []
        attacker_node_id = "DEVICE-004"

        for nid, node in net.nodes.items():
            member = member_by_dev.get(nid) or member_by_resq.get(nid)
            is_keyed = bool(member and member.signing_public_key and member.encryption_public_key)

            if node.is_attacker:
                attacker_node_id = nid

            node_summaries.append(
                DashboardNodeSummary(
                    node_id=nid,
                    device_id=getattr(member, "device_id", nid),
                    name=getattr(member, "name", f"Relay Node {nid}"),
                    team=getattr(member, "team", "Tactical Mesh"),
                    role=getattr(member, "role", "Relay Station"),
                    is_online=node.is_online,
                    is_attacker=node.is_attacker,
                    is_keyed=is_keyed,
                    neighbors=sorted(list(node.neighbors)),
                )
            )

        # Deduplicated edges
        edges_set = set()
        for node in net.nodes.values():
            for nbr in node.neighbors:
                edge = tuple(sorted([node.node_id, nbr]))
                edges_set.add(edge)
        edges = [list(e) for e in sorted(edges_set)]

        # Latest route summary
        active_route: Optional[DashboardRouteSummary] = None
        logs = net.get_delivery_logs()
        if logs:
            last_log = logs[-1]
            active_route = DashboardRouteSummary(
                route_id=f"RT-{last_log.packet_id[-6:]}",
                source=last_log.source,
                destination=last_log.destination,
                hops=last_log.route,
                hop_count=len(last_log.hops),
                status=last_log.status,
            )

        # Messaging summary — load raw data directly from repository
        raw_repo_data = self.message_service.repository._load_raw_data()
        all_msgs_raw = raw_repo_data.get("messages", [])
        from backend.app.models.messages import MessageRecord as MR
        all_msgs = []
        for item in all_msgs_raw:
            try:
                all_msgs.append(MR(**item))
            except Exception:
                continue
        total_msgs = len(all_msgs)
        delivered_count = sum(1 for m in all_msgs if m.status in (MessageStatus.DELIVERED, MessageStatus.DECRYPTED))
        in_transit_count = sum(1 for m in all_msgs if m.status in (MessageStatus.ROUTING, MessageStatus.IN_TRANSIT))
        failed_count = sum(1 for m in all_msgs if m.status == MessageStatus.FAILED)

        recent_msgs = []
        for m in reversed(all_msgs[-5:]):
            recent_msgs.append({
                "message_id": m.message_id,
                "packet_id": m.packet_id,
                "sender_id": m.sender_rescue_id,
                "recipient_id": m.recipient_rescue_id,
                "status": m.status.value,
                "created_at": m.created_at,
                "hops": m.hop_count,
            })

        messaging_summary = DashboardMessagingSummary(
            total_messages=total_msgs,
            delivered_count=delivered_count,
            in_transit_count=in_transit_count,
            failed_count=failed_count,
            recent_messages=recent_msgs,
        )

        # Security summary
        active_count = sum(1 for m in all_members if m.status == MemberStatus.ACTIVE)
        keyed_count = sum(1 for m in all_members if m.signing_public_key and m.encryption_public_key)
        revoked_count = sum(1 for m in all_members if m.status == MemberStatus.REVOKED)

        total_gate_decisions = len(SECURITY_LOGS)
        successful_decryptions = sum(1 for l in SECURITY_LOGS if l.get("event") == "MESSAGE_DECRYPTED")
        gate_success_rate = (
            round((successful_decryptions / total_gate_decisions) * 100, 1)
            if total_gate_decisions > 0
            else 100.0
        )

        recent_events = [
            f"[{l.get('event')}] Packet: {l.get('packet_id')} | Sender: {l.get('sender_id')} -> {l.get('recipient_id')}"
            + (f" | Reason: {l.get('reason')}" if l.get('reason') else " | Approved")
            for l in reversed(SECURITY_LOGS[-6:])
        ]

        security_summary = DashboardSecuritySummary(
            active_responders_count=active_count,
            keyed_devices_count=keyed_count,
            revoked_count=revoked_count,
            gate_success_rate=gate_success_rate,
            recent_security_events=recent_events,
        )

        # Attacker summary
        attack_stat = self.attack_service.get_status()
        captures = self.attack_service.list_captures()
        latest_cap_dict = None
        verdict = "No packets intercepted yet"

        if captures:
            last_c = captures[0]
            latest_cap_dict = {
                "capture_id": last_c.capture_id,
                "packet_id": last_c.packet_id,
                "mode": last_c.communication_mode,
                "captured_at_node": last_c.captured_at_node,
                "plaintext_exposed": last_c.plaintext_exposed,
                "readable_by_attacker": last_c.message_readable_by_attacker,
                "sniffed_content": last_c.sniffed_content,
                "security_result": last_c.security_result,
            }
            if last_c.message_readable_by_attacker:
                verdict = "WARNING: Plaintext exposed to eavesdropper (Vulnerable Mode)"
            else:
                verdict = "CONFIDENTIAL: Attacker captured ciphertext but cannot read message (Protected Mode)"

        attacker_summary = DashboardAttackerSummary(
            attacker_node_id=attacker_node_id,
            is_sniffing=True,
            total_intercepted=attack_stat.total_captures,
            vulnerable_captures=attack_stat.vulnerable_captures,
            protected_captures=attack_stat.protected_captures,
            latest_capture=latest_cap_dict,
            readability_verdict=verdict,
        )

        return DashboardOverviewResponse(
            timestamp=_now_iso(),
            phase=8,
            phase_name="phase-8",
            blackout_in_effect=True,
            operational_status=OperationalStatusPills(),
            nodes=node_summaries,
            edges=edges,
            active_route=active_route,
            messaging=messaging_summary,
            security=security_summary,
            attacker=attacker_summary,
            summary_takeaway="The goal is not to prevent packet capture. The goal is to ensure that capturing a packet does not reveal the emergency message.",
        )

    def quick_dispatch(self, request: QuickDispatchRequest) -> QuickDispatchResponse:
        """Atomic quick dispatch from Dashboard:
        Sends an emergency message, triggers attacker capture, passes to receiver gate, and updates overview.
        """
        mode_enum = SimulationMode.VULNERABLE if request.mode.lower() == "vulnerable" else SimulationMode.PROTECTED

        sim_req = SimulateAttackRequest(
            mode=mode_enum,
            sender_id=request.sender_id,
            recipient_id=request.recipient_id,
            message=request.message,
        )

        sim_resp = self.attack_service.simulate_attack(sim_req)
        cap = sim_resp.captured_packet

        gate_decision = (
            "AUTHORIZED_DECRYPTED"
            if sim_resp.receiver_result.get("status") in ("SUCCESS", "DELIVERED_INSECURE")
            else str(sim_resp.receiver_result.get("status", "UNKNOWN"))
        )

        overview = self.get_overview()

        return QuickDispatchResponse(
            status="DISPATCHED",
            mode=request.mode,
            packet_id=sim_resp.packet_id,
            message_id=sim_resp.message_id,
            route=sim_resp.route,
            hop_count=len(sim_resp.route),
            captured_by_attacker=sim_resp.captured,
            attacker_readable=bool(cap and cap.message_readable_by_attacker),
            attacker_sniffed=cap.sniffed_content if cap else "Not intercepted",
            security_gate_decision=gate_decision,
            decrypted_message=str(sim_resp.receiver_result.get("message") or ""),
            explanation=sim_resp.summary_sentence,
            overview=overview,
        )


dashboard_service = DashboardService()
