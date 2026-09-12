# RESQ — Secure Emergency Mesh Communication

[![Phase: 3 Cryptography Active](https://img.shields.io/badge/Phase-3%20Cryptography%20Active-06b6d4)](docs/architecture.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](backend/)
[![Frontend: React+Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb)](frontend/)
[![Tests: Pytest](https://img.shields.io/badge/Tests-47%20Passed-10b981)](tests/)

> **Hackathon Problem Statement:**
> *Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.*

RESQ is a security-focused emergency communication platform designed to protect life-critical transmissions when central communication infrastructure (cellular, internet) collapses. RESQ demonstrates how authenticated, encrypted packets can travel across multi-hop peer-to-peer mesh nodes while remaining completely unreadable to packet-sniffing adversaries.

---

## Current Status: Phase 3 (Cryptographic Security Layer)

In **Phase 3**, RESQ establishes the **Cryptographic Security Layer** for registered rescue devices:
- **Digital Signatures**: Ed25519 keypairs for message signing and identity verification.
- **Key Agreement**: X25519 Diffie-Hellman key exchange.
- **Key Derivation**: HKDF-SHA256 with per-operation random salt.
- **Authenticated Encryption**: ChaCha20-Poly1305 with per-operation fresh 12-byte nonce.
- **Envelope Security**: Versioned encryption envelopes with header-bound Authenticated Associated Data (AAD).
- **Private-Key Storage**: Local filesystem storage (`keys/<device_id>/`) using PKCS8 PEM with two-phase staging atomicity and exact rollback.
- **Public-Key Registry**: Base64 raw 32-byte public keys persisted in `data/registry.json`.

In strict adherence to the project boundaries:
- **Private keys** are never returned in APIs, logged, or exposed to the frontend.
- **No messaging, mesh relay, or packet sniffing** is active in this phase.

---

## Standardized 10-Phase Roadmap

1. **Phase 1: Foundation & Architecture** (Completed)
2. **Phase 2: Rescue Registry & Device Identities** (Completed)
3. **Phase 3: Cryptographic Security Layer** (Completed)
4. **Phase 4: Software Mesh Simulation** (Planned)
5. **Phase 5: Secure Message Transmission** (Planned)
6. **Phase 6: Authorization & Controlled Decryption** (Planned)
7. **Phase 7: Packet-Sniffing Attack Simulation** (Planned)
8. **Phase 8: Dashboard & Real-Time Visualization** (Planned)
9. **Phase 9: Security & Resilience Testing** (Planned)
10. **Phase 10: Final Integration & Demo** (Planned)

---

## API Endpoints (Phase 3)

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Health check endpoint | 200 |
| `GET` | `/api/system/info` | System information & security flags | 200 |
| `GET` | `/api/registry/members` | List all registered members | 200 |
| `POST` | `/api/registry/members` | Register new member (auto-generates IDs) | 201 |
| `GET` | `/api/registry/members/{rescue_id}` | Find member by Rescue ID | 200 / 404 |
| `GET` | `/api/registry/devices/{device_id}` | Find member by Device ID | 200 / 404 |
| `GET` | `/api/registry/members/{rescue_id}/status` | Check active status of a member | 200 / 404 |
| `POST` | `/api/registry/members/{rescue_id}/revoke` | Revoke active status (retains record) | 200 / 404 / 409 |
| `POST` | `/api/crypto/devices/{device_id}/initialize` | Provision Ed25519 & X25519 keys | 201 / 400 / 404 / 409 |
| `GET` | `/api/crypto/devices/{device_id}/status` | Check cryptographic readiness status | 200 / 404 |

---

## Running the Application

### 1. Run Automated Tests
From the project root:
```bash
python -m pytest tests/ -v
```
All 47 tests pass with 100% test isolation across temporary registry and keys storage.

### 2. Run the Backend
From the project root:
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API docs are available at `http://127.0.0.1:8000/docs`.

### 3. Run the Frontend
From the `frontend/` directory:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.