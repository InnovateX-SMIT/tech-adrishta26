#!/usr/bin/env python3
"""RESQ Phase 7 End-to-End Verification Script.

Demonstrates the core security problem RESQ is designed to solve:
1. Mode A (Vulnerable / Before RESQ):
   - Message transmitted unencrypted over the mesh network.
   - Passive packet sniffer captures the packet.
   - Attacker reads the original emergency distress message.
   - Result: Message exposed (Vulnerability demonstrated).
2. Mode B (Protected / After RESQ):
   - Message encrypted and signed using existing Phase 3/5/6 pipeline.
   - Passive packet sniffer captures the packet.
   - Attacker inspects the packet: sees ONLY ciphertext, zero plaintext.
   - Attacker has no private keys, cannot decrypt.
   - Result: Plaintext protected.
   - Authorized receiver verifies and decrypts the message via Phase 6 gate.
3. Tampering Defense:
   - Attacker alters a byte in the captured ciphertext.
   - Receiver gate rejects the modified packet with zero plaintext leaked.
4. Summary:
   - "The goal is not to prevent packet capture. The goal is to ensure that capturing a packet does not reveal the emergency message."
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.mesh_node import MeshNode
from backend.app.models.attack import SimulateAttackRequest, SimulationMode
from backend.app.services.attack_simulation_service import attack_simulation_service
from backend.app.services.crypto_service import crypto_service
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.registry_service import registry_service


def print_banner(title: str):
    print("\n" + "=" * 78)
    print(f"[*] {title}")
    print("=" * 78)


def main():
    print("\n" + "#" * 78)
    print("  RESQ EMERGENCY MESH - PHASE 7 ATTACK SIMULATION & CONTRAST MODE")
    print("#" * 78)

    # 1. Identity & Keys Bootstrap
    print_banner("Step 1: Validating Rescue Registry & Identity Keys")
    crypto_service.bootstrap_dev_identities()
    sender = registry_service.get_member_by_rescue_id("RESQ-001")
    receiver = registry_service.get_member_by_rescue_id("RESQ-002")
    attacker = registry_service.get_member_by_rescue_id("RESQ-004")

    if not sender or not receiver or not attacker:
        print("[!] Error: Required rescue members (RESQ-001, RESQ-002, RESQ-004) not found.")
        sys.exit(1)

    print(f"[+] Sender:    {sender.name} ({sender.rescue_id} / {sender.device_id})")
    print(f"[+] Recipient: {receiver.name} ({receiver.rescue_id} / {receiver.device_id})")
    print(f"[+] Attacker:  {attacker.name} ({attacker.rescue_id} / {attacker.device_id}) [Passive Sniffer]")

    # 2. Topology Setup: Sender <-> Relay <-> Attacker Tap <-> Recipient
    print_banner("Step 2: Configuring Mesh Network Topology with Attacker Sniffer Node")
    reset_network()
    net = get_network()

    relay_node = "DEVICE-RELAY-01"
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(relay_node))
    net.add_node(MeshNode(attacker.device_id, is_attacker=True))
    net.add_node(MeshNode(receiver.device_id))

    net.connect_nodes(sender.device_id, relay_node)
    net.connect_nodes(relay_node, attacker.device_id)
    net.connect_nodes(attacker.device_id, receiver.device_id)

    print(f"[+] Topology: {sender.device_id} <---> {relay_node} <---> {attacker.device_id} (Attacker) <---> {receiver.device_id}")

    # 3. Mode A: Vulnerable / Before RESQ
    print_banner("Step 3: Simulating Mode A - Before RESQ (Unsecured Vulnerable Mesh)")
    vuln_msg = "SOS: Three responders pinned under debris in Sector 4. Air supply 20 min."
    print(f"[+] Original Plaintext: \"{vuln_msg}\"")

    vuln_req = SimulateAttackRequest(
        mode=SimulationMode.VULNERABLE,
        sender_id=sender.rescue_id,
        recipient_id=receiver.rescue_id,
        message=vuln_msg,
        attacker_node_id=attacker.device_id,
    )
    vuln_res = attack_simulation_service.simulate_attack(vuln_req)
    v_cap = vuln_res.captured_packet

    print(f"[+] Transmission Status: {vuln_res.receiver_result.get('status')}")
    print(f"[+] Packet Captured:     {vuln_res.captured}")
    print(f"[+] Route Traversed:     {' -> '.join(vuln_res.route)}")
    print(f"[+] Plaintext Exposed:   {v_cap.plaintext_exposed}")
    print(f"[+] Attacker Readable:   {v_cap.message_readable_by_attacker}")
    print(f"[+] Attacker Sniffed:    \"{v_cap.sniffed_content}\"")
    print(f"[+] Security Result:     {v_cap.security_result}")
    print(f"[+] Explanation:         {v_cap.explanation}")

    assert v_cap.message_readable_by_attacker is True, "Attacker should read unencrypted message!"
    assert vuln_msg in v_cap.sniffed_content, "Attacker should have intercepted plaintext!"
    print("[+] VERIFIED: In vulnerable mode, eavesdropper successfully reads the message.")

    # 4. Mode B: Protected / After RESQ
    print_banner("Step 4: Simulating Mode B - After RESQ (Cryptographic Mesh Protection)")
    prot_msg = "CONFIDENTIAL DISPATCH: Evacuation corridor Charlie open. Grid 44-N, 12-E."
    print(f"[+] Original Plaintext: \"{prot_msg}\"")

    prot_req = SimulateAttackRequest(
        mode=SimulationMode.PROTECTED,
        sender_id=sender.rescue_id,
        recipient_id=receiver.rescue_id,
        message=prot_msg,
        attacker_node_id=attacker.device_id,
    )
    prot_res = attack_simulation_service.simulate_attack(prot_req)
    p_cap = prot_res.captured_packet

    print(f"[+] Transmission Status: {prot_res.receiver_result.get('status')}")
    print(f"[+] Packet Captured:     {prot_res.captured}")
    print(f"[+] Route Traversed:     {' -> '.join(prot_res.route)}")
    print(f"[+] Contains Plaintext:  {p_cap.contains_plaintext}")
    print(f"[+] Plaintext Exposed:   {p_cap.plaintext_exposed}")
    print(f"[+] Ciphertext Present:  {p_cap.ciphertext_present}")
    print(f"[+] Signature Present:   {p_cap.signature_present}")
    print(f"[+] Attacker Readable:   {p_cap.message_readable_by_attacker}")
    print(f"[+] Attacker Sniffed:    {p_cap.sniffed_content}")
    print(f"[+] Security Result:     {p_cap.security_result}")
    print(f"[+] Receiver Decryption: {prot_res.receiver_result.get('message')}")

    assert p_cap.message_readable_by_attacker is False, "Attacker must NOT be able to read protected message!"
    assert p_cap.contains_plaintext is False, "Protected packet must NOT contain plaintext!"
    assert prot_msg not in str(p_cap.model_dump()), "CRITICAL: Plaintext leaked in protected capture record!"
    assert prot_res.receiver_result.get("status") == "SUCCESS", "Receiver should decrypt successfully!"
    assert prot_res.receiver_result.get("message") == prot_msg, "Receiver decrypted text mismatch!"
    print("[+] VERIFIED: In protected mode, attacker sees only ciphertext. Receiver decrypts successfully.")

    # 5. Tampering Defense Demonstration
    print_banner("Step 5: Defense Demonstration - Modifying Captured Ciphertext")
    tamper_res = attack_simulation_service.tamper_capture(
        capture_id=p_cap.capture_id,
        tamper_field="ciphertext",
        recipient_id=receiver.device_id,
    )
    print(f"[+] Tamper Target:       Field '{tamper_res.tampered_field}'")
    print(f"[+] Receiver Gate:       {tamper_res.receiver_status} (Reason: {tamper_res.rejection_reason})")
    print(f"[+] Rejection Detail:    {tamper_res.rejection_detail}")
    print(f"[+] Plaintext Leaked:    {tamper_res.plaintext_revealed}")
    print(f"[+] Explanation:         {tamper_res.explanation}")

    assert tamper_res.receiver_status == "REJECTED", "Tampered packet must be rejected!"
    assert tamper_res.plaintext_revealed is False, "Tampered packet must not reveal plaintext!"
    print("[+] VERIFIED: Altered packet is rejected by Phase 6 receiver gate.")

    # 6. Conclusion
    print("\n" + "=" * 78)
    print("  KEY PRESENTATION TAKEAWAY:")
    print("  \"The goal is not to prevent packet capture. The goal is to ensure")
    print("   that capturing a packet does not reveal the emergency message.\"")
    print("=" * 78)
    print("\nALL PHASE 7 ATTACK SIMULATION & CONTRAST MODE CHECKS PASSED PERFECTLY!\n")


if __name__ == "__main__":
    main()
