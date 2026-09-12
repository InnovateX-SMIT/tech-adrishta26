#!/usr/bin/env python3
"""RESQ Phase 6 End-to-End Verification Script.

Demonstrates the entire emergency mesh security lifecycle:
1. Active Member & Key Bootstrapping
2. Multi-Hop Mesh Network Routing
3. Secure Message Transmission (X25519 + HKDF-SHA256 + ChaCha20-Poly1305 + Ed25519)
4. Wire Packet Inspection (Zero plaintext leakage)
5. Attacker Interception Simulation (Confidentiality proof)
6. Phase 6 Decryption Gate 6-Step Verification:
   - Check 1: Sender Registry Lookup
   - Check 2: Sender Status Validation
   - Check 3: Ed25519 Signature Verification over RFC 8785 Canonical JSON
   - Check 4: Recipient Authorization
   - Check 5: Protocol-Level Replay & Timestamp Drift Protection
   - Check 6: Authenticated ChaCha20-Poly1305 Decryption
7. Controlled Plaintext Release
8. Tamper & Replay Attack Defense Demonstrations
"""

import sys
import time
import base64
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.decryption_gate import process_incoming_packet, clear_replay_cache
from backend.app.core.mesh_node import MeshNode
from backend.app.services.crypto_service import crypto_service
from backend.app.services.message_service import message_service
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.registry_service import registry_service


def print_step(title: str):
    print(f"\n{'='*75}\n[*] {title}\n{'='*75}")


def main():
    print("\n" + "#"*75)
    print("  RESQ EMERGENCY MESH - PHASE 6 END-TO-END SECURITY VERIFICATION")
    print("#"*75)

    # Step 1: Bootstrap identities and keys
    print_step("Step 1: Bootstrapping Development Keys & Registry")
    count = crypto_service.bootstrap_dev_identities()
    print(f"[+] Bootstrapped private keys on disk for {count} devices in keys/ directory.")

    sender = registry_service.get_member_by_rescue_id("RESQ-001")
    receiver = registry_service.get_member_by_rescue_id("RESQ-002")
    attacker = registry_service.get_member_by_rescue_id("RESQ-004")

    if not sender or not receiver or not attacker:
        print("[!] Error: Required default members not found in registry.")
        sys.exit(1)

    print(f"[+] Sender:    {sender.name} ({sender.rescue_id} / {sender.device_id}) [Status: {sender.status.value}]")
    print(f"[+] Recipient: {receiver.name} ({receiver.rescue_id} / {receiver.device_id}) [Status: {receiver.status.value}]")
    print(f"[+] Attacker:  {attacker.name} ({attacker.rescue_id} / {attacker.device_id}) [Status: {attacker.status.value}]")

    # Step 2: Mesh topology
    print_step("Step 2: Configuring Multi-Hop Mesh Network Topology")
    reset_network()
    clear_replay_cache()
    net = get_network()

    relay_id = "DEVICE-RELAY-01"
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(relay_id))
    net.add_node(MeshNode(receiver.device_id))
    net.add_node(MeshNode(attacker.device_id, is_attacker=True))

    # Path: Sender -> Relay -> Attacker (passive monitor) -> Recipient
    net.connect_nodes(sender.device_id, relay_id)
    net.connect_nodes(relay_id, attacker.device_id)
    net.connect_nodes(attacker.device_id, receiver.device_id)

    print(f"[+] Topology: {sender.device_id} <---> {relay_id} <---> {attacker.device_id} (Attacker Tap) <---> {receiver.device_id}")

    # Step 3: Secure message transmission
    print_step("Step 3: Composing & Encrypting Authenticated Emergency Distress Message")
    emergency_text = "MAYDAY MAYDAY: Structural collapse at Sector 7-G. 4 casualties. Need medical transport."
    print(f"[+] Plaintext (origin): \"{emergency_text}\"")

    send_resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=receiver.rescue_id,
        message=emergency_text,
    )
    payload = send_resp.payload

    print(f"[+] Transmission Status: {send_resp.status}")
    print(f"[+] Packet ID:           {send_resp.packet_id}")
    print(f"[+] Message ID:          {send_resp.message_id}")
    print(f"[+] Mesh Hops Taken:     {len(send_resp.hop_log)}")
    for h in send_resp.hop_log:
        print(f"    Hop #{h.hop_number}: {h.from_node} -> {h.to_node}")

    # Step 4: Wire packet inspection
    print_step("Step 4: Inspecting Wire Packet Payload (Zero Plaintext Leakage)")
    print(f"[+] Algorithm:            {payload.cipher} with {payload.kdf} & {payload.key_agreement}")
    print(f"[+] Ephemeral Public Key: {payload.ephemeral_public_key[:24]}... (32 bytes Base64)")
    print(f"[+] HKDF Salt:            {payload.salt} (16 bytes Base64)")
    print(f"[+] Nonce:                {payload.nonce} (12 bytes Base64)")
    print(f"[+] Ciphertext:           {payload.ciphertext[:32]}... ({len(payload.ciphertext)} chars Base64)")
    print(f"[+] Ed25519 Signature:    {payload.signature[:32]}... (64 bytes Base64)")

    # Assert zero plaintext in payload
    assert emergency_text not in str(payload.model_dump()), "CRITICAL: Plaintext leaked in payload!"
    print("[+] VERIFIED: Zero plaintext characters found in the transmitted mesh packet.")

    # Step 5: Attacker eavesdropping proof
    print_step("Step 5: Passive Interception by Intermediate Attacker Node")
    attacker_node = net.nodes[attacker.device_id]
    captured_count = len(attacker_node.captured_packets)
    print(f"[+] Attacker Node '{attacker.device_id}' intercepted {captured_count} packet(s).")
    if captured_count > 0:
        captured_payload = attacker_node.captured_packets[0].payload
        print(f"[+] Attacker captured ciphertext: {captured_payload.get('ciphertext', '')[:32]}...")
        print("[+] Attacker lacks receiver's private key -> CANNOT decrypt.")

    # Step 6: Recipient inbox & Phase 6 gate
    print_step("Step 6: Executing Phase 6 Authorization Gate on Recipient Device")
    gate_result = process_incoming_packet(
        packet=payload.model_dump(),
        current_receiver_id=receiver.device_id,
    )

    print(f"[+] Gate Decision: {gate_result['status']}")
    if gate_result["status"] == "SUCCESS":
        print(f"[+] Authenticated Sender:   {gate_result['sender_name']} ({gate_result['sender_id']})")
        print(f"[+] Decrypted Message:      \"{gate_result['message']}\"")
        assert gate_result["message"] == emergency_text, "Decrypted text mismatch!"
        print("[+] SUCCESS: Plaintext released ONLY after passing all 6 authorization gate checks!")
    else:
        print(f"[!] Decryption failed: {gate_result.get('reason')}")
        sys.exit(1)

    # Step 7: Tamper defense
    print_step("Step 7: Defense Verification - Tampered Ciphertext Attack")
    tampered_dict = payload.model_dump()
    raw_ct = bytearray(base64.b64decode(tampered_dict["ciphertext"]))
    raw_ct[5] ^= 0xFF  # Corrupt 1 byte
    tampered_dict["ciphertext"] = base64.b64encode(raw_ct).decode("utf-8")

    tamper_result = process_incoming_packet(
        packet=tampered_dict,
        current_receiver_id=receiver.device_id,
    )
    print(f"[+] Tamper Test Result: Status={tamper_result['status']}, Reason={tamper_result.get('reason')}")
    assert tamper_result["status"] == "REJECTED"
    assert "message" not in tamper_result
    print("[+] VERIFIED: Tampered packet rejected cleanly. Zero plaintext leaked.")

    # Step 8: Replay attack defense
    print_step("Step 8: Defense Verification - Protocol-Level Replay Attack")
    replay_result = process_incoming_packet(
        packet=payload.model_dump(),
        current_receiver_id=receiver.device_id,
    )
    print(f"[+] Replay Test Result: Status={replay_result['status']}, Reason={replay_result.get('reason')}")
    assert replay_result["status"] == "REJECTED"
    assert replay_result.get("reason") == "REPLAY_ATTACK_DETECTED"
    print("[+] VERIFIED: Replay attack blocked by Phase 6 cache tracking.")

    print("\n" + "="*75)
    print("  PHASE 6 END-TO-END SECURITY PIPELINE FULLY VERIFIED AND OPERATIONAL!")
    print("="*75 + "\n")


if __name__ == "__main__":
    main()
