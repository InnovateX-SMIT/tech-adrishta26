# RESQ Architecture & Security Specification

## 1. Problem Statement & Threat Model

### Problem Statement
During critical infrastructure collapse or extreme blackout scenarios (natural disasters, grid failures, tactical disruptions), traditional centralized communication channels (cellular towers, fiber backhauls, cloud internet) become unavailable. First responders rely on ad-hoc peer-to-peer (P2P) mesh networks to relay distress signals, coordinate medical triage, and dispatch rescue teams.

However, standard unencrypted P2P mesh protocols broadcast packets indiscriminately across peer nodes. Any malicious actor or rogue station within radio range can passively sniff the packet stream, intercepting sensitive operational intel, patient medical identities, and responder locations without authorization.

### Project Objective
**RESQ** provides an end-to-end authenticated, encrypted communication architecture layered over ad-hoc peer-to-peer mesh networks. Authorized emergency messages traverse multi-hop intermediate nodes while remaining unreadable to packet-sniffing adversaries, ensuring only verified and authorized rescue units can decrypt and act upon life-critical communications.

---

## 2. Security Boundaries & Architectural Invariants

The implementation adheres strictly to the following architectural boundaries:

1. **Sender-Side End-to-End Encryption**: Message content encryption occurs entirely on the sender device before any packet is queued for mesh transmission (Phase 5).
2. **Authorized Receiver Decryption**: Decryption occurs exclusively at the intended, authenticated recipient node possessing the corresponding private key (Phase 6).
3. **Zero-Knowledge Intermediate Mesh Forwarding**: Intermediate mesh hops store and forward encrypted packets without decrypting them, maintaining payload confidentiality across the entire hop topology (Phase 4).
4. **Attacker Simulation Realism**: The packet-sniffing adversary intercepts raw transmitted mesh packets over the wire, but cannot decrypt message payloads due to the absence of device private keys (Phase 7).
5. **Public-Only Centralized/Distributed Registry**: The registry stores only public identities and public cryptographic keys (signing and encryption).
6. **Local Isolation of Private Keys**: Device private keys (e.g., Ed25519 signing keys, X25519 static/ephemeral keypairs) remain exclusively within the local secure boundary of the respective device. Private keys are never transmitted across the mesh, uploaded to the registry, or exposed in frontend code.
7. **Simulation Scope**: The hackathon demonstration utilizes an in-process / software-based peer-to-peer mesh simulation to illustrate multi-hop routing, packet forwarding, and sniffing vulnerability without requiring physical LoRa / SDR radio hardware.
8. **Blackout Resilience Assumption**: The core communication and verification model operates autonomously without relying on external internet connectivity or centralized third-party SaaS authentication services.
9. **Metadata Realism**: The system protects message contents (payload confidentiality and authenticity). It does not claim to obscure routing metadata (such as packet IDs, sender IDs, hop headers, or transmission timestamps) necessary for mesh propagation.
10. **Standard Cryptography Only**: No custom cryptographic primitives are implemented. All cryptographic operations leverage established, audited algorithms from Python's standard `cryptography` library (Ed25519 for digital signatures/authentication, X25519 for key agreement, and AES-256-GCM / ChaCha20-Poly1305 for authenticated symmetric encryption).
11. **Administrative Device Identity Boundary**: In Phase 2, "device identity" signifies an administrative registry record identified by a unique Device ID. It does not confer cryptographic authentication, proof of ownership, or proof of origin until cryptographic keypairs are introduced in Phase 3.

---

## 3. Phase 2: Trusted Rescue Registry & Administrative Device Identities

### Implemented Functionality
- **Safe JSON Persistence**: Atomic file writes via temporary file replacement (`backend/app/storage/json_store.py`) targeting `data/registry.json`.
- **Administrative Identifiers**:
  - `rescue_id`: Auto-generated unique format (`RESQ-001`, `RESQ-002`, etc.) with gap detection that never reuses retired IDs.
  - `device_id`: Auto-generated unique format (`DEVICE-001`, `DEVICE-002`, etc.).
- **Strict Input Validation**: Rejection of empty or whitespace-only inputs (`name`, `team`, `role`). Unknown fields (including any attempted private-key injection) are rejected with HTTP 422 (`extra="forbid"`).
- **Public-Key Placeholders**: `signing_public_key` and `encryption_public_key` are strictly server-controlled and initialized to `null`.
- **Lifecycle Management**:
  - `status`: Strictly `"active"` or `"revoked"`.
  - `revoked_at`: Records UTC ISO 8601 timestamp upon revocation.
  - Historical records are preserved indefinitely upon revocation (never deleted).
  - Repeated revocation returns HTTP 409 Conflict.

### Registry Schema (`data/registry.json`)
```json
{
  "version": 1,
  "members": [
    {
      "rescue_id": "RESQ-001",
      "name": "Aarav Sharma",
      "team": "Rescue Unit A",
      "role": "Field Responder",
      "device_id": "DEVICE-001",
      "signing_public_key": null,
      "encryption_public_key": null,
      "status": "active",
      "created_at": "2026-09-12T10:00:00+00:00",
      "revoked_at": null
    }
  ]
}
```

### Phase 2 Strict Scope Limitations
- ❌ No Ed25519 key generation
- ❌ No X25519 key generation
- ❌ No AES-GCM or ChaCha20-Poly1305 encryption/decryption
- ❌ No digital signatures or verification
- ❌ No private-key generation, storage, or transmission
- ❌ No mesh routing or multi-hop forwarding
- ❌ No emergency message creation or dispatch
- ❌ No packet sniffing or attacker simulation

---

## 4. Future Cryptographic Contracts (Phase 3 Preview)

> [!NOTE]
> The specifications below are planned for Phase 3 and beyond. They are not active in Phase 2.

### Cryptographic Identity Allocation
In Phase 3:
- **Ed25519**: Used exclusively for digital signatures and authentication of message packets.
- **X25519**: Used exclusively for Diffie-Hellman key agreement to derive symmetric keys via HKDF-SHA256.
- **Private Keys**: Stored in strictly isolated, gitignored device files (`keys/<device_id>.json`). Never uploaded to the registry.

### Future Encrypted Packet Specification (Planned for Phase 5)
```json
{
  "packet_id": "PKT-1001",
  "message_id": "MSG-1001",
  "sender_id": "RESQ-001",
  "recipient_id": "RESQ-002",
  "timestamp": 1773300000,
  "ephemeral_public_key": "<base64-x25519-ephemeral-key>",
  "nonce": "<base64-12-byte-iv>",
  "ciphertext": "<base64-authenticated-ciphertext>",
  "signature": "<base64-ed25519-signature>"
}
```

---

## 5. Standardized 10-Phase Architectural Roadmap

| Phase | Designation | Status | Objective |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Foundation & Architecture | **COMPLETED** | FastAPI backend, Vite/React frontend, atomic JSON store, tests, baseline health. |
| **Phase 2** | Registry & Administrative Device IDs | **COMPLETED** | Member registry, unique RESQ/DEVICE IDs, active/revoked lifecycle, management UI. |
| **Phase 3** | Cryptographic Identity & Key Management | *PLANNED* | Ed25519 signing keypairs, X25519 key agreement, isolated local private-key storage. |
| **Phase 4** | Software Mesh Simulation | *PLANNED* | Multi-hop peer-to-peer network simulation with hop-by-hop zero-knowledge relay. |
| **Phase 5** | Secure Message Transmission | *PLANNED* | Authenticated payload encryption (AES-GCM / ChaCha20) and Ed25519 packet signing. |
| **Phase 6** | Authorization & Controlled Decryption | *PLANNED* | Recipient registry verification, active status checks, and authorized payload decryption. |
| **Phase 7** | Packet-Sniffing Attack Simulation | *PLANNED* | Side-by-side comparison: plaintext mesh sniffing vs RESQ cryptographic confidentiality. |
| **Phase 8** | Dashboard & Real-Time Visualization | *PLANNED* | Interactive tactical map, live mesh topology, event timeline, and audit logs. |
| **Phase 9** | Security & Resilience Testing | *PLANNED* | Tamper detection tests, replay attack mitigation, and revoked-key rejection tests. |
| **Phase 10** | Final Integration & Demo | *PLANNED* | Comprehensive disaster scenario walkthrough ready for hackathon presentation. |
