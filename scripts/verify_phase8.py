#!/usr/bin/env python3
"""
verify_phase8.py — Phase 8 Dashboard & Real-Time Visualization Verification Script

Demonstrates dashboard telemetry aggregation, quick dispatch lifecycle,
attacker packet interception, and receiver decryption gate in a single CLI run.

Usage:
    python verify_phase8.py
    python verify_phase8.py --base-url http://127.0.0.1:8000
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("[FATAL] 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _divider(title: str, char: str = "─") -> None:
    width = 72
    side = (width - len(title) - 2) // 2
    print(f"\n{char * side} {title} {char * (width - side - len(title) - 2)}")


def _print_json(data: dict, indent: int = 2) -> None:
    print(json.dumps(data, indent=indent, default=str))


def _check(condition: bool, ok_msg: str, fail_msg: str) -> bool:
    if condition:
        print(f"  ✅  {ok_msg}")
    else:
        print(f"  ❌  {fail_msg}")
    return condition


def verify_overview(base: str) -> dict:
    _divider("STEP 1 — Dashboard Overview Telemetry")
    resp = requests.get(f"{base}/api/dashboard/overview", timeout=10)
    resp.raise_for_status()
    data = resp.json()

    print(f"\n  Phase: {data['phase']} ({data['phase_name']})")
    print(f"  Blackout Active: {data['blackout_in_effect']}")

    ops = data["operational_status"]
    print(f"\n  Operational Status Pills:")
    print(f"    🔴 Cellular Network : {ops['cellular_network']} [{ops['cellular_status'].upper()}]")
    print(f"    🟢 Emergency Mesh   : {ops['emergency_mesh']} [{ops['mesh_status'].upper()}]")
    print(f"    🔐 Encryption       : {ops['encryption']} [{ops['encryption_status'].upper()}]")
    print(f"    ✅ Identity Auth    : {ops['identity_authority']} [{ops['identity_status'].upper()}]")
    print(f"    🔓 Controlled Decrypt: {ops['controlled_decryption']} [{ops['decryption_status'].upper()}]")

    print(f"\n  Mesh Nodes ({len(data['nodes'])} total):")
    for node in data["nodes"]:
        marker = "🕵 ATTACKER" if node["is_attacker"] else ("🟢" if node["is_online"] else "🔴")
        keyed = "🔑 KEYED" if node["is_keyed"] else "⚠ UNKEYED"
        print(f"    {marker}  {node['node_id']} ({node['name']}) — {keyed} — neighbors: {node['neighbors']}")

    m = data["messaging"]
    print(f"\n  Messaging Summary:")
    print(f"    Total: {m['total_messages']}  Delivered: {m['delivered_count']}  "
          f"In-Transit: {m['in_transit_count']}  Failed: {m['failed_count']}")

    s = data["security"]
    print(f"\n  Security Summary:")
    print(f"    Active Responders: {s['active_responders_count']}  "
          f"Keyed: {s['keyed_devices_count']}  "
          f"Revoked: {s['revoked_count']}  "
          f"Gate Pass Rate: {s['gate_success_rate']}%")

    a = data["attacker"]
    print(f"\n  Attacker Summary:")
    print(f"    Sniffer: {a['attacker_node_id']}  Sniffing: {a['is_sniffing']}")
    print(f"    Captured: {a['total_intercepted']}  Protected: {a['protected_captures']}  Vulnerable: {a['vulnerable_captures']}")
    print(f"    Verdict: {a['readability_verdict']}")

    print(f"\n  Takeaway: \"{data['summary_takeaway']}\"")

    _check(data["phase"] == 8, "Phase = 8", "Phase mismatch")
    _check(data["blackout_in_effect"], "Blackout in effect", "Blackout not active")
    _check(ops["cellular_status"] == "offline", "Cellular OFFLINE", "Cellular status wrong")
    _check(ops["mesh_status"] == "active", "Mesh ACTIVE", "Mesh status wrong")
    _check(ops["encryption_status"] == "active", "Encryption ACTIVE", "Encryption status wrong")
    _check(len(data["nodes"]) > 0, f"{len(data['nodes'])} mesh nodes found", "No mesh nodes")

    return data


def verify_quick_dispatch_protected(base: str, sender: str, recipient: str) -> dict:
    _divider("STEP 2 — Quick Dispatch (Protected Mode)")
    msg = "SOS: Three people trapped in Building B. Air supply 20 minutes. Send rescue team immediately."
    payload = {
        "mode": "protected",
        "sender_id": sender,
        "recipient_id": recipient,
        "message": msg,
    }
    print(f"\n  Sender: {sender} → Recipient: {recipient}")
    print(f"  Message: \"{msg[:60]}...\"")

    resp = requests.post(f"{base}/api/dashboard/quick-dispatch", json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    print(f"\n  Dispatch Result:")
    print(f"    Status         : {data['status']}")
    print(f"    Mode           : {data['mode']}")
    print(f"    Packet ID      : {data['packet_id']}")
    print(f"    Route          : {' → '.join(data['route'])} ({data['hop_count']} hops)")
    print(f"    Captured       : {data['captured_by_attacker']}")
    print(f"    Attacker Sniffed: {data['attacker_sniffed'][:80]}...")
    print(f"    Attacker Readable: {data['attacker_readable']}")
    print(f"    Gate Decision  : {data['security_gate_decision']}")
    print(f"    Decrypted Msg  : \"{data.get('decrypted_message', '')}\"")
    print(f"    Explanation    : {data['explanation']}")

    _check(data["status"] == "DISPATCHED", "Status = DISPATCHED", f"Status = {data['status']}")
    _check(data["mode"] == "protected", "Mode = protected", f"Mode = {data['mode']}")
    _check(data["captured_by_attacker"], "Packet captured by attacker (expected)", "Packet NOT captured")
    _check(not data["attacker_readable"], "Attacker CANNOT read (protected)", "⚠ Attacker CAN read — breach!")
    _check(
        data["security_gate_decision"] == "AUTHORIZED_DECRYPTED",
        "Gate: AUTHORIZED_DECRYPTED",
        f"Gate: {data['security_gate_decision']}"
    )
    _check(data["decrypted_message"] == msg, "Plaintext matches original", "Plaintext mismatch")
    _check(data["overview"]["phase"] == 8, "Overview refreshed (phase=8)", "Overview stale")

    return data


def verify_quick_dispatch_vulnerable(base: str, sender: str, recipient: str) -> dict:
    _divider("STEP 3 — Quick Dispatch (Vulnerable / Contrast Mode)")
    msg = "UNENCRYPTED: Medical supplies needed at Outpost 2. Send logistics team."
    payload = {
        "mode": "vulnerable",
        "sender_id": sender,
        "recipient_id": recipient,
        "message": msg,
    }
    print(f"\n  Sender: {sender} → Recipient: {recipient}")
    print(f"  Message: \"{msg}\"")

    resp = requests.post(f"{base}/api/dashboard/quick-dispatch", json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    print(f"\n  Dispatch Result:")
    print(f"    Mode            : {data['mode']}")
    print(f"    Attacker Sniffed: {data['attacker_sniffed'][:100]}")
    print(f"    Attacker Readable: {data['attacker_readable']}")

    _check(data["mode"] == "vulnerable", "Mode = vulnerable", f"Mode = {data['mode']}")
    _check(data["captured_by_attacker"], "Packet captured (expected)", "Not captured")
    _check(data["attacker_readable"], "Attacker CAN read plaintext (expected for vulnerable)", "Attacker cannot read")

    return data


def verify_metrics_update(base: str, sender: str, recipient: str) -> None:
    _divider("STEP 4 — Metrics Truthfulness Check")

    before = requests.get(f"{base}/api/dashboard/overview", timeout=10).json()
    before_captures = before["attacker"]["total_intercepted"]
    before_msgs = before["messaging"]["total_messages"]
    print(f"\n  Before dispatch — Captures: {before_captures}  Messages: {before_msgs}")

    payload = {
        "mode": "protected",
        "sender_id": sender,
        "recipient_id": recipient,
        "message": "Telemetry consistency verification test.",
    }
    requests.post(f"{base}/api/dashboard/quick-dispatch", json=payload, timeout=20).raise_for_status()

    after = requests.get(f"{base}/api/dashboard/overview", timeout=10).json()
    after_captures = after["attacker"]["total_intercepted"]
    after_msgs = after["messaging"]["total_messages"]
    print(f"  After dispatch  — Captures: {after_captures}  Messages: {after_msgs}")

    _check(after_captures == before_captures + 1, "Capture count +1 ✓", f"Expected {before_captures + 1}, got {after_captures}")
    _check(after_msgs >= before_msgs + 1, "Message count incremented ✓", "Message count did not increment")
    _check(after.get("active_route") is not None, "Active route populated ✓", "Active route is None")
    if after.get("active_route"):
        print(f"  Active Route: {after['active_route']['source']} → {after['active_route']['destination']} via {after['active_route']['hops']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8 Dashboard Verification Script")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--sender", default="RESQ-001", help="Sender RESQ ID")
    parser.add_argument("--recipient", default="RESQ-002", help="Recipient RESQ ID")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    print("=" * 72)
    print("  RESQ PHASE 8 — Dashboard & Real-Time Visualization Verification")
    print("=" * 72)
    print(f"  Backend: {base}")
    print(f"  Sender:  {args.sender}  |  Recipient: {args.recipient}")

    failures: list[str] = []

    try:
        verify_overview(base)
    except Exception as e:
        print(f"\n  [FATAL] Overview check failed: {e}")
        failures.append("overview")

    try:
        verify_quick_dispatch_protected(base, args.sender, args.recipient)
    except Exception as e:
        print(f"\n  [FATAL] Protected dispatch failed: {e}")
        failures.append("protected_dispatch")

    try:
        verify_quick_dispatch_vulnerable(base, args.sender, args.recipient)
    except Exception as e:
        print(f"\n  [FATAL] Vulnerable dispatch failed: {e}")
        failures.append("vulnerable_dispatch")

    try:
        verify_metrics_update(base, args.sender, args.recipient)
    except Exception as e:
        print(f"\n  [FATAL] Metrics check failed: {e}")
        failures.append("metrics")

    _divider("SUMMARY", "═")
    if not failures:
        print("\n  🎉  All Phase 8 dashboard checks PASSED.")
        print("  Tactical Command Dashboard is production-ready.")
    else:
        print(f"\n  ⚠️  {len(failures)} check(s) FAILED: {', '.join(failures)}")
        print("  Ensure the backend is running: uvicorn backend.app.main:app --port 8000")
        sys.exit(1)

    print("=" * 72)


if __name__ == "__main__":
    main()
