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
6. **Local Isolation of Private Keys**: Device private keys (Ed25519 signing keys, X25519 static keypairs) remain exclusively within the local secure boundary of the respective device. Private keys are never transmitted across the mesh, uploaded to the registry, exposed in frontend code, or returned via APIs.
7. **Simulation Scope**: The hackathon demonstration utilizes an in-process / software-based peer-to-peer mesh simulation to illustrate multi-hop routing, packet forwarding, and sniffing vulnerability without requiring physical LoRa / SDR radio hardware.
8. **Blackout Resilience Assumption**: The core communication and verification model operates autonomously without relying on external internet connectivity or centralized third-party SaaS authentication services.
9. **Metadata Realism**: The system protects message contents (payload confidentiality and authenticity). It does not claim to obscure routing metadata (such as packet IDs, sender IDs, hop headers, or transmission timestamps) necessary for mesh propagation.
10. **Standard Cryptography Only**: No custom cryptographic primitives are implemented. All cryptographic operations leverage established, audited algorithms from Python's standard `cryptography` library:
    - **Ed25519**: Digital signatures and sender authenticity.
    - **X25519**: Diffie-Hellman key agreement.
    - **HKDF-SHA256**: Key derivation with per-message random salt.
    - **ChaCha20-Poly1305**: Authenticated symmetric encryption with fresh 12-byte nonce.
11. **Private-Key Storage Transparency**: Local storage in `keys/<device_id>/` is an unencrypted PKCS8 PEM development-level prototype protected by filesystem access controls. It is not hardware-backed (HSM/TPM) and not encrypted at rest.

---

## 3. Phase 3 Cryptographic Security Layer Specification

### A. Device Cryptographic Keypairs
Each registered device is provisioned with two distinct long-term keypairs:
1. **Signing Keypair (Ed25519)**:
   - Private key: stored locally on the host device at `keys/<device_id>/signing_private.pem` (PKCS8 PEM).
   - Public key: Base64-encoded raw 32 bytes registered in `data/registry.json` as `signing_public_key`.
   - Used for signing emergency messages, proving sender authenticity, and non-repudiation.
2. **Key Agreement Keypair (X25519)**:
   - Private key: stored locally on the host device at `keys/<device_id>/encryption_private.pem` (PKCS8 PEM).
   - Public key: Base64-encoded raw 32 bytes registered in `data/registry.json` as `encryption_public_key`.
   - Used for Diffie-Hellman key agreement with ephemeral sender keys to derive symmetric encryption keys.

### B. Authenticated Encryption Construction
Every encryption operation executes the following sequence:
1. Generate a fresh ephemeral X25519 keypair (`ephemeral_priv`, `ephemeral_pub`).
2. Generate a fresh random 16-byte HKDF salt (`os.urandom(16)`).
3. Compute X25519 shared secret: `derive_shared_secret(ephemeral_priv, recipient_pub)`.
4. Derive 32-byte symmetric key via HKDF-SHA256 using the salt and `info=b"resq-chacha20-poly1305-v1"`.
5. Generate a fresh random 12-byte nonce (`os.urandom(12)`).
6. Build Authenticated Associated Data (AAD) using the shared canonical helper `build_envelope_aad`:
   ```text
   header_aad = f"{version}|{key_agreement}|{kdf}|{cipher}|{ephemeral_public_key}|{salt}|{nonce}".encode("utf-8")
   total_aad = header_aad + (b":" + caller_aad_b64 if caller_aad_b64 else b"")
   ```
7. Encrypt plaintext (including support for empty plaintext `b""`) with ChaCha20-Poly1305.
8. Output self-contained `EncryptionEnvelope`.

### C. Encryption Envelope Schema
```json
{
  "version": 1,
  "key_agreement": "X25519",
  "kdf": "HKDF-SHA256",
  "cipher": "ChaCha20-Poly1305",
  "ephemeral_public_key": "<base64-32-bytes>",
  "salt": "<base64-16-bytes>",
  "nonce": "<base64-12-bytes>",
  "ciphertext": "<base64-ciphertext-with-16-byte-poly1305-tag>",
  "associated_data": "<optional-base64-caller-aad>"
}
```

### D. Key Provisioning Lifecycle & Atomicity
- **Two-Phase Staging**: Private keys are written to a temporary staging folder (`keys/.staging_<device_id>_<uuid>/`). Public keys are validated (32 raw bytes) and written to `data/registry.json`. Once persisted, the staging directory is renamed to `keys/<device_id>/`. If any step fails, the staging directory is purged and the registry is rolled back to its exact prior state.
- **Two-Sided Key Verification**: Before initialization, both disk key files and registry public-key fields are checked. If all 4 exist, the local private keys are loaded and public keys derived; if they match registry, HTTP 409 Conflict is returned (already initialized). If mismatched or partially populated, HTTP 409 is returned for inconsistent key state requiring manual intervention.

---

## 4. Standardized 10-Phase Architectural Roadmap

| Phase | Designation | Status | Objective |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Foundation & Architecture | **COMPLETED** | FastAPI backend, Vite/React frontend, atomic JSON store, tests, baseline health. |
| **Phase 2** | Registry & Administrative Device IDs | **COMPLETED** | Member registry, unique RESQ/DEVICE IDs, active/revoked lifecycle, management UI. |
| **Phase 3** | Cryptographic Security Layer | **COMPLETED** | Ed25519 signatures, X25519 key agreement, HKDF-SHA256, ChaCha20-Poly1305 envelopes, staging atomicity. |
| **Phase 4** | Software Mesh Simulation | *PLANNED* | Multi-hop peer-to-peer network simulation with hop-by-hop zero-knowledge relay. |
| **Phase 5** | Secure Message Transmission | *PLANNED* | Authenticated payload encryption and Ed25519 packet signing over mesh topologies. |
| **Phase 6** | Authorization & Controlled Decryption | *PLANNED* | Recipient registry verification, active status checks, and authorized payload decryption. |
| **Phase 7** | Packet-Sniffing Attack Simulation | *PLANNED* | Side-by-side comparison: plaintext mesh sniffing vs RESQ cryptographic confidentiality. |
| **Phase 8** | Dashboard & Real-Time Visualization | *PLANNED* | Interactive tactical map, live mesh topology, event timeline, and audit logs. |
| **Phase 9** | Security & Resilience Testing | *PLANNED* | Tamper detection tests, replay attack mitigation, and revoked-key rejection tests. |
| **Phase 10** | Final Integration & Demo | *PLANNED* | Comprehensive disaster scenario walkthrough ready for hackathon presentation. |

---

## 5. Phase 3 Scope & Known Limitations

### What Phase 3 Implements:
- Device signing-key generation (Ed25519)
- Device encryption key generation (X25519)
- Digital signatures and signature verification with safe error semantics
- Authenticated encryption and decryption (ChaCha20-Poly1305 + HKDF-SHA256)
- Shared canonical AAD construction preventing envelope tampering
- Empty plaintext support (`b""`)
- Local development private-key filesystem storage (`keys/<device_id>/`)
- Two-phase staging with exact registry rollback
- Public-key registration in `data/registry.json`
- 29 unit and integration tests covering tampering, key exchange, and failure modes

### Explicitly Deferred to Future Phases:
- ❌ No peer-to-peer mesh routing or packet relay (Phase 4)
- ❌ No emergency message dispatch or broadcast (Phase 5)
- ❌ No recipient access-control matrices or authorization policies (Phase 6)
- ❌ No packet sniffing adversary simulation (Phase 7)
- ❌ No hardware-backed key storage (HSM / TPM)
- ❌ No automated key rotation or certificate authority infrastructure
