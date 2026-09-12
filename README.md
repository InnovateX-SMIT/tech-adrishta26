# RESQ — Secure Emergency Mesh Communication

[![Phase: 2 Registry Active](https://img.shields.io/badge/Phase-2%20Registry%20Active-06b6d4)](docs/architecture.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](backend/)
[![Frontend: React+Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb)](frontend/)
[![Tests: Pytest](https://img.shields.io/badge/Tests-18%20Passed-10b981)](tests/)

> **Hackathon Problem Statement:**
> *Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.*

RESQ is a security-focused emergency communication platform designed to protect life-critical transmissions when central communication infrastructure (cellular, internet) collapses. RESQ demonstrates how authenticated, encrypted packets can travel across multi-hop peer-to-peer mesh nodes while remaining completely unreadable to packet-sniffing adversaries.

---

## Current Status: Phase 2 (Rescue Registry & Device Identities)

In **Phase 2**, RESQ establishes the **Trusted Rescue-Team Registry and Administrative Device Identifiers**. Responders can be registered, assigned auto-generated collision-safe Rescue IDs (`RESQ-001`) and Device IDs (`DEVICE-001`), and managed through active and revoked states while preserving full historical records.

In strict adherence to the project boundaries:
- **"Device identity"** currently signifies an administrative registry record, not cryptographic authentication.
- **Public-key fields** (`signing_public_key`, `encryption_public_key`) are server-controlled placeholders (`null`) awaiting Phase 3.
- **No private keys** are stored or generated.
- **No messaging, mesh relay, or packet sniffing** is active in this phase.

---

## Standardized 10-Phase Roadmap

1. **Phase 1: Foundation & Architecture** (Completed)
2. **Phase 2: Rescue Registry & Device Identities** (Completed)
3. **Phase 3: Cryptographic Identity & Key Management** (Planned)
4. **Phase 4: Software Mesh Simulation** (Planned)
5. **Phase 5: Secure Message Transmission** (Planned)
6. **Phase 6: Authorization & Controlled Decryption** (Planned)
7. **Phase 7: Packet-Sniffing Attack Simulation** (Planned)
8. **Phase 8: Dashboard & Real-Time Visualization** (Planned)
9. **Phase 9: Security & Resilience Testing** (Planned)
10. **Phase 10: Final Integration & Demo** (Planned)

---

## Project Structure

```text
tech-adrishta26/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py        # GET /api/health
│   │   │       ├── system.py        # GET /api/system/info
│   │   │       └── registry.py      # /api/registry/* (CRUD, lookup, revoke)
│   │   ├── core/                    # Core primitives
│   │   ├── models/
│   │   │   ├── schemas.py           # Health & SystemInfo schemas
│   │   │   └── registry.py          # RescueMember, RegisterMemberRequest, MemberStatusResponse
│   │   ├── services/
│   │   │   └── registry_service.py  # Member registration, unique ID generator, revocation
│   │   ├── storage/
│   │   │   └── json_store.py        # Safe atomic JSON storage helper
│   │   ├── config.py                # Environment & CORS configuration
│   │   └── main.py                  # FastAPI application factory
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── services/api.ts          # Centralized API service with timeout & error handling
│   │   ├── types/index.ts           # TypeScript definitions
│   │   ├── App.tsx                  # RESQ Foundation & Registry Management page
│   │   ├── index.css                # Cyber-tactical emergency design system
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── data/
│   ├── registry.json                # Local JSON registry store
│   └── demo/                        # Placeholder for future simulation scenarios
│
├── keys/
│   └── .gitkeep                     # Gitkeep marker (private keys are strictly excluded)
│
├── docs/
│   ├── architecture.md              # Threat model, data contracts, and security boundaries
│   └── problem/problemStatement.txt # Hackathon problem statement
│
├── tests/
│   ├── test_health.py               # Health endpoint & CORS tests
│   ├── test_system_info.py          # System info & security boundary verification
│   ├── test_json_store.py           # Atomic JSON store, unicode, and error tests
│   ├── test_registry.py             # Phase 2 registration, validation, lookup, and revocation
│   └── README.md
│
├── pytest.ini                       # Pytest configuration from root
├── .gitignore                       # Git hygiene (protects private keys, venvs, cache)
├── .env.example                     # Root environment example
└── README.md
```

---

## API Endpoints (Phase 2)

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Health check endpoint | 200 |
| `GET` | `/api/system/info` | System information & security flags | 200 |
| `GET` | `/api/registry/members` | List all registered members (active & revoked) | 200 |
| `POST` | `/api/registry/members` | Register new member (auto-generates IDs) | 201 |
| `GET` | `/api/registry/members/{rescue_id}` | Find member by exact Rescue ID | 200 / 404 |
| `GET` | `/api/registry/devices/{device_id}` | Find member by exact Device ID | 200 / 404 |
| `GET` | `/api/registry/members/{rescue_id}/status` | Check active status of a member | 200 / 404 |
| `POST` | `/api/registry/members/{rescue_id}/revoke` | Revoke active status (retains record) | 200 / 404 / 409 |

---

## Running the Application

### 1. Run Automated Tests
From the project root:
```bash
python -m pytest tests/ -v
```
All 18 tests pass with 100% test isolation.

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