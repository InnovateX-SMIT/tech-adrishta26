# RESQ — Zero-Trust Emergency Mesh Network & Secure Communication

[![Zero-Trust Security](https://img.shields.io/badge/Security-100%25%20Zero--Trust-10b981?style=flat-square)](docs/architecture.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)](backend/)
[![Frontend: React + Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb?style=flat-square)](frontend/)
[![Cryptography](https://img.shields.io/badge/Cryptography-X25519%20%2B%20ChaCha20--Poly1305%20%2B%20Ed25519-indigo?style=flat-square)](backend/app/services/crypto_service.py)

> **Problem Statement:**
> *Unencrypted peer-to-peer mesh networks are vulnerable to packet sniffing and unauthorized interception during blackouts and infrastructure collapse.*

---

## Overview

**RESQ** is a high-assurance emergency communication platform designed to protect life-critical transmissions when central communications infrastructure (cellular towers, commercial internet) is down. In disaster situations, rescue personnel must communicate over ad-hoc wireless mesh relays where nodes may be unvetted, compromised, or eavesdropped on.

RESQ solves this through a **Zero-Trust Peer-to-Peer architecture**:
- Every transmission is cryptographically signed (**Ed25519**) and authenticated-encrypted (**X25519 Ephemeral Key Agreement + HKDF-SHA256 + ChaCha20-Poly1305 AEAD**).
- Intermediate relay nodes forward encrypted packets without ever being able to read or tamper with the payload.
- Captured packets reveal **zero plaintext** to eavesdroppers.
- A **Strict 6-Step Decryption Gate** guarantees that only verified, active, and authorized recipients can decrypt emergency communications.

---

## Contrast Demonstration: Vulnerable vs Protected Mode

RESQ features a built-in attack simulation to directly demonstrate the difference between legacy unencrypted mesh networks and the RESQ Zero-Trust architecture:

| Capability | Legacy Unencrypted Mesh (Mode A) | RESQ Zero-Trust Mesh (Mode B) |
| :--- | :--- | :--- |
| **Transmission** | Plaintext transmitted over mesh relays | Authenticated X25519 + ChaCha20-Poly1305 AEAD |
| **Packet Sniffing** | ⚠️ **Critical Vulnerability**: Attacker captures packet and reads emergency message directly | 🛡️ **Protected**: Attacker captures wire packet but sees **only high-entropy ciphertext** |
| **Identity Verification** | None (spoofable sender fields) | RFC 8785 Canonical JSON signed with Ed25519 private keys |
| **Tampering Resistance** | None (packets can be altered in transit undetected) | Rejected at receiver gate (AEAD authentication tag / Ed25519 signature failure) |
| **Replay Defense** | Vulnerable to replayed distress calls | Blocked via unique `packet_id` tracking and timestamp drift limits |
| **Revocation Enforcement** | None | Real-time registry check blocks revoked responder keys instantly |

> *"The goal is not to prevent packet capture. In a broadcast wireless medium, packet capture is inevitable. The goal is to ensure that capturing a packet reveals zero plaintext."*

---

## Core System Architecture

### 1. Cryptographic Security Engine
- **Asymmetric Signing**: Ed25519 keypairs for verifiable sender identity.
- **Key Agreement**: Ephemeral X25519 ECDH key exchange generates fresh, unrepeatable shared secrets per transmission.
- **Key Derivation**: HKDF-SHA256 with 16-byte random salts derives 256-bit symmetric encryption keys.
- **Symmetric AEAD**: ChaCha20-Poly1305 with random 12-byte nonces provides authenticated encryption with integrity protection.
- **Canonical Serialization**: RFC 8785 canonical JSON formatting prevents signature malleability.
- **Wire Encoding**: Uniform Base64 standard for all keys, salts, nonces, ciphertexts, and digital signatures.

### 2. Multi-Hop Software Mesh Simulation
- Dynamic peer-to-peer network graph with BFS shortest-path routing.
- Packet relay with configurable TTL (Time-To-Live) and hop limit enforcement.
- Node outage resilience: disable relays on the fly and verify rerouting around dead zones.
- Attacker taps: passive sniffing nodes capture passing packets for real-time security auditing.

### 3. Strict 6-Step Decryption Gate
Plaintext is released **only** when all six verification gates pass:
```
[ Incoming Packet ]
       │
       ▼
 1. Sender Registry Lookup       ──(Unknown Sender)──► [ REJECT ]
       │
       ▼
 2. Sender Status Validation     ──(Revoked Member)──► [ REJECT ]
       │
       ▼
 3. Ed25519 Signature Check      ──(Tampered Wire)───► [ REJECT ]
       │
       ▼
 4. Recipient Authorization      ──(Wrong Node)──────► [ REJECT ]
       │
       ▼
 5. Replay Attack Prevention     ──(Duplicate ID)────► [ REJECT ]
       │
       ▼
 6. ChaCha20-Poly1305 Decrypt    ──(Corrupt AEAD)────► [ REJECT ]
       │
       ▼
[ Plaintext Released to Recipient ]
```

---

## Tactical Operations Dashboard (Frontend)

The frontend is a dark-mode, tactical web application built with **React**, **Vite**, **TypeScript**, and **Tailwind CSS**:

1. **Mesh Simulation**:
   - Interactive canvas visualizer of topology relays, links, and hops.
   - Node status toggling (simulate relay outage / offline state).
   - Real-time path tracing from source to destination.

2. **Secure Transmit**:
   - Emergency message composer with responder identity selector.
   - Live wire-packet payload inspector (headers, cryptographic fields, signatures).
   - Recipient inbox with interactive **6-Step Gate verification breakdown**.

3. **Attack Simulation & Contrast Mode**:
   - Side-by-side execution: **Vulnerable (Cleartext)** vs **Protected (Encrypted)**.
   - Eavesdropper packet sniffer log displaying intercepted packets in real time.
   - Active tamper testing: mutate captured bytes and prove receiver gate rejection.

4. **Device Registry**:
   - Responder management (Name, Team, Role, Rescue ID, Device ID).
   - On-demand cryptographic keypair provisioning.
   - Instant access revocation for compromised devices.

---

## REST API Reference

### 🔒 Messaging & Decryption Gate
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/messages/send` | Sign, encrypt (X25519 + ChaCha20), and route message across mesh |
| `GET` | `/api/messages/inbox/{recipient_id}` | List encrypted packets waiting in recipient inbox |
| `POST` | `/api/messages/decrypt` | Authorize and decrypt emergency message (6-step gate) |
| `GET` | `/api/messages/{message_id}/status` | Track multi-hop delivery and decryption status |

### 🎯 Attack Simulation (Contrast Mode)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/attack/simulate` | Run vulnerable vs protected transmission simulation |
| `GET` | `/api/attack/captures` | List all packets intercepted by the passive sniffer |
| `GET` | `/api/attack/captures/{capture_id}` | Retrieve detailed captured packet breakdown |
| `POST` | `/api/attack/captures/{id}/tamper` | Mutate captured payload and test receiver rejection |
| `GET` | `/api/attack/status` | Get real-time attack simulation metrics |
| `DELETE`| `/api/attack/reset` | Clear simulation history and captures |

### 📊 Dashboard & Telemetry
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/dashboard/overview` | Unified real-time telemetry, mesh state, and security status |
| `POST` | `/api/dashboard/quick-dispatch` | Atomic dispatch with immediate sniffer and gate evaluation |

### 👥 Registry & Cryptographic Identity
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/registry/members` | List all registered rescue personnel |
| `POST` | `/api/registry/members` | Enroll responder with auto-generated Rescue & Device IDs |
| `GET` | `/api/registry/members/{rescue_id}` | Lookup member by Rescue ID |
| `POST` | `/api/registry/members/{rescue_id}/revoke` | Revoke member credentials |
| `POST` | `/api/crypto/devices/{device_id}/initialize` | Provision Ed25519 & X25519 keypairs |
| `GET` | `/api/crypto/devices/{device_id}/status` | Check cryptographic key provisioning status |

### 🌐 Mesh Simulation
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/mesh/topology` | Fetch current mesh nodes, edges, and statuses |
| `POST` | `/api/mesh/demo` | Provision standard 5-node demo topology |
| `GET` | `/api/mesh/routes/{src}/{dst}` | Compute shortest path route via BFS |
| `PATCH`| `/api/mesh/nodes/{node_id}` | Toggle node online/offline or relay status |
| `GET` | `/api/mesh/node/{id}/inbox` | View node-specific packet reception queue |
| `DELETE`| `/api/mesh/reset` | Reset mesh topology to default state |

---

## Quick Start & Running Locally

### Prerequisites
- **Python 3.10+** (with `fastapi`, `uvicorn`, `cryptography`, `pydantic`)
- **Node.js 18+** & **npm**

### 1. Run the Backend API
From the root directory:
```bash
# Start FastAPI backend with hot-reload
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger / OpenAPI docs are available at **http://127.0.0.1:8000/docs**.

### 2. Run the Frontend Application
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** to access the tactical operations interface.

### 3. Run Verification Scripts
Standalone CLI scripts demonstrate end-to-end proofs without external dependencies:

```bash
# Run End-to-End Encryption & 6-Step Gate Verification
python3 verify_phase6.py

# Run Packet Sniffing & Attack Simulation Verification
python3 verify_phase7.py
```

### 4. Run Automated Tests
```bash
pytest tests/ -v
```

---

## Security Audit & Compliance

- **Zero Plaintext Wire Exposure**: All emergency payload data is encrypted prior to entering the mesh network layer.
- **Ephemeral Forward Secrecy**: Fresh ephemeral X25519 keys prevent historic traffic decryption if static keys are compromised.
- **Collision-Resistant Canonicalization**: RFC 8785 canonical JSON ensures deterministic byte-level representation before signature computation.
- **Graceful Failure**: Rejection at any step in the decryption gate triggers immediate drop without disclosing underlying cryptographic states.