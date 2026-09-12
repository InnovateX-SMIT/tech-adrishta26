# RESQ — Secure Emergency Mesh Communication

[![Phase: 6 End-to-End Encryption Active](https://img.shields.io/badge/Phase-6%20End--to--End%20Encryption%20Active-10b981)](docs/architecture.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](backend/)
[![Frontend: React+Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb)](frontend/)
[![Tests: Pytest](https://img.shields.io/badge/Tests-160%20Passed-10b981)](tests/)

> **Hackathon Problem Statement:**
> *Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.*

RESQ is a security-focused emergency communication platform designed to protect life-critical transmissions when central communication infrastructure (cellular, internet) collapses. RESQ demonstrates how authenticated, encrypted packets travel across multi-hop peer-to-peer mesh nodes while remaining completely unreadable to packet-sniffing adversaries and protected against tampering and replay attacks.

---

## Current Status: Phase 6 (End-to-End Secure Transmission & Controlled Decryption Gate)

In **Phase 6**, RESQ establishes the complete end-to-end cryptographic and mesh pipeline:
- **X25519 Key Agreement & ChaCha20-Poly1305 AEAD**: Generates fresh ephemeral keys and random 16-byte HKDF salts per transmission, creating one-time 256-bit symmetric keys with 12-byte nonces.
- **RFC 8785 Canonical JSON & Ed25519 Digital Signatures**: Deterministically serializes 12 payload fields for collision-free cryptographic binding.
- **Protocol-Level Base64 Wire Encoding**: Clean, uniform Base64 standard for all keys, salts, nonces, ciphertexts, and signatures.
- **Multi-Hop Mesh Forwarding**: BFS routing through relays (e.g. `NODE-1 -> RELAY -> NODE-2`) without exposing plaintext to intermediate hops.
- **Strict 6-Step Decryption Gate**:
  1. Sender registry lookup (rejects unknown identities)
  2. Sender status check (rejects revoked members)
  3. Ed25519 signature verification (rejects tampered headers or ciphertexts)
  4. Recipient authorization check (enforces intended recipient)
  5. Protocol replay protection (seen `packet_id`/`message_id` and timestamp drift window)
  6. Authenticated ChaCha20-Poly1305 decryption (rejects corrupted AEAD tags)
- **Controlled Plaintext Release**: Plaintext is decrypted and released **only** when all 6 gate checks pass. Zero plaintext or private keys are ever leaked in API responses, logs, or mesh packets.
- **Interactive UI**: Secure Message Composer, Wire Packet Payload Inspector, Recipient Inbox, and 6-Step Gate Visualizer in React + Vite.

---

## Standardized 10-Phase Roadmap

1. **Phase 1: Foundation & Architecture** (Completed)
2. **Phase 2: Rescue Registry & Device Identities** (Completed)
3. **Phase 3: Cryptographic Security Layer** (Completed)
4. **Phase 4: Software Mesh Simulation** (Completed)
5. **Phase 5: Secure Message Transmission** (Completed)
6. **Phase 6: Authorization Gate & Controlled Decryption** (Completed & Active)
7. **Phase 7: Packet-Sniffing Attack Simulation** (Planned)
8. **Phase 8: Dashboard & Real-Time Visualization** (Planned)
9. **Phase 9: Security & Resilience Testing** (Planned)
10. **Phase 10: Final Integration & Demo** (Planned)

---

## REST API Endpoints (Phase 6)

### Messaging & Decryption Gate
| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/messages/send` | Encrypt, sign, and dispatch secure message across mesh | 200 / 400 / 404 / 422 |
| `GET` | `/api/messages/inbox/{recipient_id}` | Retrieve encrypted packets in recipient node inbox | 200 / 404 |
| `POST` | `/api/messages/decrypt` | Authorize and decrypt emergency message (Phase 6 Gate) | 200 / 400 / 404 |

### Registry & Cryptographic Identity
| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/registry/members` | List all registered members | 200 |
| `POST` | `/api/registry/members` | Register new member (auto-generates IDs) | 201 |
| `GET` | `/api/registry/members/{rescue_id}` | Find member by Rescue ID | 200 / 404 |
| `GET` | `/api/registry/devices/{device_id}` | Find member by Device ID | 200 / 404 |
| `POST` | `/api/registry/members/{rescue_id}/revoke` | Revoke active status (retains record) | 200 / 404 / 409 |
| `POST` | `/api/crypto/devices/{device_id}/initialize` | Provision Ed25519 & X25519 keys | 201 / 400 / 404 / 409 |
| `GET` | `/api/crypto/devices/{device_id}/status` | Check cryptographic readiness status | 200 / 404 |

### Mesh Simulation & Observability
| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/mesh/topology` | Retrieve nodes, edges, and online status | 200 |
| `POST` | `/api/mesh/demo` | Build standard demo topology | 200 |
| `GET` | `/api/mesh/routes/{src}/{dst}` | Pure route discovery (BFS shortest path) | 200 / 404 / 422 |
| `PATCH`| `/api/mesh/nodes/{node_id}` | Update node online & relay states | 200 / 404 |
| `POST` | `/api/mesh/send` | Simulate packet transmission with TTL enforcement | 200 / 404 / 422 |
| `GET` | `/api/mesh/node/{id}/inbox` | Retrieve packets delivered to node inbox | 200 / 404 |
| `GET` | `/api/mesh/node/{id}/captured` | Retrieve eavesdropped packets (attacker tap) | 200 / 404 |
| `GET` | `/api/mesh/logs` | Retrieve delivery audit event log | 200 |
| `DELETE`| `/api/mesh/reset` | Clear simulation mesh topology and state | 200 |

---

## Running the Application

### 1. Run Automated Test Suite
From the project root:
```bash
python -m pytest tests/ -v
```
All **160 tests** pass cleanly in ~3 seconds.

### 2. Run Phase 6 Standalone Verification
```bash
python verify_phase6.py
```
Demonstrates complete end-to-end transmission, multi-hop mesh routing, wire confidentiality proof, 6-step gate authorization, and tamper/replay attack defense.

### 3. Run the Backend Service
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### 4. Run the Frontend UI
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` to explore the Mesh Topology, Secure Message Composer, Wire Packet Inspector, and Phase 6 Decryption Gate.