# RESQ Architecture & Security Specification

## 1. Problem Statement & Threat Model

### Problem Statement
During critical infrastructure collapse or extreme blackout scenarios (natural disasters, grid failures, tactical disruptions), traditional centralized communication channels (cellular towers, fiber backhauls, cloud internet) become unavailable. First responders rely on ad-hoc peer-to-peer (P2P) mesh networks to relay distress signals, coordinate medical triage, and dispatch rescue teams.

However, standard unencrypted P2P mesh protocols broadcast packets indiscriminately across peer nodes. Any malicious actor or rogue station within radio range can passively sniff the packet stream, intercepting sensitive operational intel, patient medical identities, and responder locations without authorization.

### Project Objective
**RESQ** provides an end-to-end authenticated, encrypted communication architecture layered over ad-hoc peer-to-peer mesh networks. Authorized emergency messages traverse multi-hop intermediate nodes while remaining unreadable to packet-sniffing adversaries, ensuring only verified and authorized rescue units can decrypt and act upon life-critical communications.

---

## 2. Security Boundaries & Architectural Invariants

The implementation adheres strictly to the following 10 architectural boundaries:

1. **Sender-Side End-to-End Encryption**: Message content encryption occurs entirely on the sender device before any packet is queued for mesh transmission.
2. **Authorized Receiver Decryption**: Decryption occurs exclusively at the intended, authenticated recipient node possessing the corresponding private key.
3. **Zero-Knowledge Intermediate Mesh Forwarding**: Intermediate mesh hops store and forward encrypted packets without decrypting them, maintaining payload confidentiality across the entire hop topology.
4. **Attacker Simulation Realism**: The packet-sniffing adversary intercepts raw transmitted mesh packets over the wire, but cannot decrypt message payloads due to the absence of device private keys.
5. **Public-Only Centralized/Distributed Registry**: The registry stores only public identities and public cryptographic keys (signing and encryption).
6. **Local Isolation of Private Keys**: Device private keys (e.g., Ed25519 signing keys, X25519 static/ephemeral keypairs) remain exclusively within the local secure boundary of the respective device. Private keys are never transmitted across the mesh, uploaded to the registry, or exposed in frontend code.
7. **Simulation Scope**: The hackathon demonstration utilizes an in-process / software-based peer-to-peer mesh simulation to illustrate multi-hop routing, packet forwarding, and sniffing vulnerability without requiring physical LoRa / SDR radio hardware.
8. **Blackout Resilience Assumption**: The core communication and verification model operates autonomously without relying on external internet connectivity or centralized third-party SaaS authentication services.
9. **Metadata Realism**: The system protects message contents (payload confidentiality and authenticity). It does not claim to obscure routing metadata (such as packet IDs, sender IDs, hop headers, or transmission timestamps) necessary for mesh propagation.
10. **Standard Cryptography Only**: No custom cryptographic primitives are implemented. All cryptographic operations in future phases will leverage established, audited algorithms from Python's standard `cryptography` library (e.g., Ed25519 for digital signatures, X25519 + HKDF for key agreement, and AES-256-GCM / ChaCha20-Poly1305 for authenticated encryption).

---

## 3. Future Data Contracts (Planned for Later Phases)

> [!NOTE]
> The contracts below represent conceptual specifications for upcoming phases. They are not active in Phase 1.

### A. Rescue Registry Contract
The registry catalogues authorized responders and rescue units. It contains strictly public identity and public key materials:

```json
{
  "version": 1,
  "members": [
    {
      "rescue_id": "RESQ-001",
      "name": "Capt. Elena Rostova",
      "team": "Search & Rescue Alpha",
      "role": "Field Incident Commander",
      "device_id": "DEV-ALPHA-01",
      "signing_public_key": "MCowBQYDK2VwAyEA9k2s...[base64-encoded-ed25519-public-key]",
      "encryption_public_key": "MC4CAQAwBQYDK2VuBCIEI...[base64-encoded-x25519-public-key]",
      "status": "active"
    }
  ]
}
```

- **`signing_public_key`**: Used by receivers to verify message authenticity and integrity.
- **`encryption_public_key`**: Used by senders to derive shared symmetric encryption keys via ECDH key agreement.
- **`status`**: `"active"` or `"revoked"`. Revoked keys prevent message acceptance.

### B. Future Encrypted Packet Contract
During mesh transmission, an emergency packet encapsulates ciphertext, ephemeral key exchange parameters, and the sender's digital signature:

```json
{
  "packet_id": "PKT-1001",
  "message_id": "MSG-1001",
  "sender_id": "RESQ-001",
  "recipient_id": "RESQ-002",
  "timestamp": 1773300000,
  "ephemeral_public_key": "base64-encoded-ephemeral-x25519-key",
  "nonce": "base64-encoded-initialization-vector",
  "ciphertext": "base64-encoded-authenticated-ciphertext",
  "signature": "base64-encoded-ed25519-signature"
}
```

*Note:* In Phase 1, no mock or placeholder packets are transmitted. The exact field serialization will be integrated in Phase 3 (Cryptography) following the X25519 + HKDF-SHA256 + AES-GCM / ChaCha20-Poly1305 specification.

---

## 4. Future Security Flow (Conceptual)

```text
               +-----------------------------+
               |   Emergency Message Input   |
               | (Triage report, GPS coords) |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |   Sender-Side Encryption    |
               |  (X25519 ECDH + Auth Enc)   |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |      Digital Signature      |
               |      (Ed25519 Signing)      |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |      Encrypted Packet       |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |     Mesh Hop Forwarding     |
               |   (Zero-knowledge relay)    |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |   Receiver Verification     |
               |  (Ed25519 Signature Check)  |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |       Registry Check        |
               |  (Sender active & trusted?) |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |      Access Evaluation      |
               | (Recipient authorized role) |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               | Receiver Payload Decryption |
               | (Recipient Private Key +    |
               | Ephemeral Public Key)       |
               +--------------+--------------+
                              |
                              v
               +-----------------------------+
               |   Original Plaintext Read   |
               +-----------------------------+
```

---

## 5. Phase 1 Scope & Implementation Status

| Feature / Capability | Phase 1 Status | Target Phase |
| :--- | :--- | :--- |
| Project Foundation & Layout | **Implemented** | Phase 1 |
| FastAPI Backend & Health APIs | **Implemented** | Phase 1 |
| Automated Pytest Test Suite | **Implemented** | Phase 1 |
| Safe Atomic JSON Storage Helper | **Implemented** | Phase 1 |
| Frontend Status Dashboard | **Implemented** | Phase 1 |
| Configurable CORS & API Base URL | **Implemented** | Phase 1 |
| Responder Registry Management | *Planned* | Phase 2 |
| Cryptographic Identity & Key Gen | *Planned* | Phase 2 |
| X25519 Key Agreement & Encryption | *Planned* | Phase 3 |
| Ed25519 Digital Signatures | *Planned* | Phase 3 |
| Mesh Multi-Hop Simulation | *Planned* | Phase 4 |
| Packet Sniffer / Attacker View | *Planned* | Phase 5 |
| Full Live Emergency Dashboard | *Planned* | Phase 6 |
