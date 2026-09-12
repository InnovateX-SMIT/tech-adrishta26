# RESQ — Secure Emergency Mesh Communication

[![Phase: 1 Foundation](https://img.shields.io/badge/Phase-1%20Foundation%20Active-06b6d4)](docs/architecture.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](backend/)
[![Frontend: React+Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb)](frontend/)
[![Tests: Pytest](https://img.shields.io/badge/Tests-8%20Passed-10b981)](tests/)

> **Hackathon Problem Statement:**
> *Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.*

RESQ is a security-focused emergency communication platform designed to protect life-critical transmissions when central communication infrastructure (cellular, internet) collapses. RESQ demonstrates how authenticated, encrypted packets can travel across multi-hop peer-to-peer mesh nodes while remaining completely unreadable to packet-sniffing adversaries.

---

## Current Status: Phase 1 (Project Foundation & Architecture)

In **Phase 1**, the clean architecture, storage foundation, testing framework, documentation, and communication contracts are established. In strict adherence to the implementation roadmap, **cryptographic key generation, encryption/decryption, mesh forwarding, and attacker simulation are intentionally not active in Phase 1** and are scheduled for subsequent phases.

All endpoints and the UI accurately report Phase 1 state (`mesh_enabled: false`, `encryption_enabled: false`).

---

## Project Structure

```text
tech-adrishta26/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py        # GET /api/health
│   │   │       └── system.py        # GET /api/system/info
│   │   ├── core/                    # Security & utility primitives
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic request/response schemas
│   │   ├── services/                # Business & mesh logic
│   │   ├── storage/
│   │   │   └── json_store.py        # Safe atomic JSON storage helper
│   │   ├── config.py                # Environment & CORS configuration
│   │   └── main.py                  # FastAPI application factory
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── services/
│   │   │   └── api.ts               # Reusable API client with timeout & error handling
│   │   ├── types/
│   │   │   └── index.ts             # TypeScript definitions
│   │   ├── App.tsx                  # RESQ Foundation & Status page
│   │   ├── index.css                # Cyber-tactical emergency design system
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── data/
│   ├── registry.json                # Initial registry store (version 1, empty members)
│   └── demo/                        # Placeholder for future simulation scenarios
│
├── keys/
│   └── .gitkeep                     # Gitkeep marker (private keys are strictly excluded)
│
├── docs/
│   └── architecture.md              # Full threat model, data contracts, and security boundaries
│
├── tests/
│   ├── test_health.py               # Health endpoint & CORS tests
│   ├── test_system_info.py          # System info & security boundary verification
│   ├── test_json_store.py           # Atomic JSON store, unicode, and error tests
│   └── README.md
│
├── pytest.ini                       # Pytest configuration from root
├── .gitignore                       # Git hygiene (protects private keys, venvs, cache)
├── .env.example                     # Root environment example
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** (Tested on Python 3.14)
- **Node.js 18+** and **npm**

---

### Running the Backend

1. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Start the FastAPI server:
   ```bash
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. Verify API in browser or curl:
   - **Health:** `http://127.0.0.1:8000/api/health`
   - **System Info:** `http://127.0.0.1:8000/api/system/info`
   - **Interactive API Docs:** `http://127.0.0.1:8000/docs`

---

### Running the Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start Vite development server:
   ```bash
   npm run dev
   ```

4. Open the application:
   - Web UI: `http://localhost:5173`

---

### Running Tests

Execute the automated test suite from the project root:

```bash
python -m pytest tests/ -v
```

All 8 tests should pass:
- `test_health.py`: Verifies status 200, service ID, phase, and development CORS headers.
- `test_system_info.py`: Verifies system metadata and asserts `encryption_enabled == False` and `mesh_enabled == False`.
- `test_json_store.py`: Verifies atomic writes, directory auto-creation, UTF-8 safety, missing file handling, and malformed JSON error handling.

---

## Security Boundaries & Rules

1. **Sender-side Encryption**: Message encryption happens at the sender before mesh transmission.
2. **Authorized Receiver Decryption**: Decryption occurs only at the authorized destination node.
3. **Zero-Knowledge Forwarding**: Intermediate mesh hops relay packets without decrypting them.
4. **Attacker Realism**: Packet-sniffing adversaries capture raw wire traffic but lack private decryption keys.
5. **Public-Only Registry**: The central registry stores only public IDs and public keys; private keys remain strictly local to device storage.
6. **No Custom Cryptography**: All future cryptographic operations will utilize Python's standard `cryptography` library (X25519, Ed25519, AES-GCM / ChaCha20-Poly1305).
7. **Simulation Scope**: Mesh communication is executed as a high-fidelity software simulation.
8. **Blackout Autonomy**: Core functionality does not rely on active internet or external clouds.

See [docs/architecture.md](docs/architecture.md) for detailed contracts and security specifications.