# RESQ — Secure Emergency Mesh Communication

[![Phase: 4 Mesh Simulation Active](https://img.shields.io/badge/Phase-4%20Mesh%20Simulation%20Active-06b6d4)](docs/architecture.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](backend/)
[![Frontend: React+Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb)](frontend/)
[![Tests: Pytest](https://img.shields.io/badge/Tests-120%20Passed-10b981)](tests/)

> **Hackathon Problem Statement:**
> *Unencrypted peer-to-peer mesh network vulnerable to packet sniffing during a blackout.*

RESQ is a security-focused emergency communication platform designed to protect life-critical transmissions when central communication infrastructure (cellular, internet) collapses. RESQ demonstrates how authenticated, encrypted packets can travel across multi-hop peer-to-peer mesh nodes while remaining completely unreadable to packet-sniffing adversaries.

---

## Current Status: Phase 4 (Software Mesh Simulation)

In **Phase 4**, RESQ establishes the **Software Mesh Simulation** layer:
- **Decentralized Topology Simulation**: In-memory undirected graph representing rescue devices and links without hardware dependencies.
- **BFS Shortest-Path Routing**: Multi-hop routing algorithm avoiding cycles and disconnected partitions.
- **Node Availability & Outage Resilience**: Real-time `is_online` and `is_available_for_relay` states with dynamic rerouting around failed nodes.
- **Hop Count & TTL Enforcement**: Every forward decrements TTL; packets are expired if TTL is exhausted before delivery.
- **Passive Link Eavesdropping**: Simulated adversarial packet sniffing on shared links (e.g. `NODE-B <-> NODE-C`) demonstrating raw packet vulnerability prior to Phase 5 encryption.
- **Interactive UI**: Neon dark-mode SVG mesh canvas with hop animations, route discovery, node inspector, and event audit logs.

Strict boundary enforcement:
- **Zero real wireless hardware** (software simulation only).
- **Private cryptographic keys** remain stored locally and are never transmitted across mesh hops or exposed to APIs.
- **No user chat or conversation UI** (reserved for Phase 5).

---

## Standardized 10-Phase Roadmap

1. **Phase 1: Foundation & Architecture** (Completed)
2. **Phase 2: Rescue Registry & Device Identities** (Completed)
3. **Phase 3: Cryptographic Security Layer** (Completed)
4. **Phase 4: Software Mesh Simulation** (Completed)
5. **Phase 5: Secure Message Transmission** (Planned)
6. **Phase 6: Authorization & Controlled Decryption** (Planned)
7. **Phase 7: Packet-Sniffing Attack Simulation** (Planned)
8. **Phase 8: Dashboard & Real-Time Visualization** (Planned)
9. **Phase 9: Security & Resilience Testing** (Planned)
10. **Phase 10: Final Integration & Demo** (Planned)

---

## API Endpoints (Phase 4)

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Health check endpoint | 200 |
| `GET` | `/api/system/info` | System information & security flags | 200 |
| `GET` | `/api/registry/members` | List all registered members | 200 |
| `POST` | `/api/registry/members` | Register new member (auto-generates IDs) | 201 |
| `GET` | `/api/registry/members/{rescue_id}` | Find member by Rescue ID | 200 / 404 |
| `GET` | `/api/registry/devices/{device_id}` | Find member by Device ID | 200 / 404 |
| `POST` | `/api/registry/members/{rescue_id}/revoke` | Revoke active status (retains record) | 200 / 404 / 409 |
| `POST` | `/api/crypto/devices/{device_id}/initialize` | Provision Ed25519 & X25519 keys | 201 / 400 / 404 / 409 |
| `GET` | `/api/crypto/devices/{device_id}/status` | Check cryptographic readiness status | 200 / 404 |
| `GET` | `/api/mesh/topology` | Retrieve nodes, edges, and online status | 200 |
| `POST` | `/api/mesh/demo` | Build standard demo topology (NODE-A..E + ATTACKER) | 200 |
| `GET` | `/api/mesh/routes/{src}/{dst}` | Pure route discovery (BFS shortest path) | 200 / 404 / 422 |
| `PATCH`| `/api/mesh/nodes/{node_id}` | Update node online & relay states | 200 / 404 |
| `POST` | `/api/mesh/send` | Simulate packet transmission with TTL enforcement | 200 / 404 / 422 |
| `POST` | `/api/mesh/links` | Create bidirectional link between nodes | 200 / 400 / 404 |
| `DELETE`| `/api/mesh/links/{a}/{b}` | Disconnect link between two nodes | 200 / 404 |
| `GET` | `/api/mesh/node/{id}/inbox` | Retrieve packets delivered to node inbox | 200 / 404 |
| `GET` | `/api/mesh/node/{id}/captured` | Retrieve eavesdropped packets (attacker) | 200 / 404 |
| `GET` | `/api/mesh/logs` | Retrieve delivery audit event log | 200 |
| `POST` | `/api/mesh/reset` | Clear simulation mesh topology and state | 200 |

---

## Running the Application

### 1. Run Automated Tests
From the project root:
```bash
python -m pytest tests/ -v
```
All 120 tests pass cleanly in under 3 seconds.

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