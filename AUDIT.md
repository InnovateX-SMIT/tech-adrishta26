# RESQ PHASE 1–3 AUDIT

## Overall Status

* **Phase 1 (Foundation & Architecture):** 🟡 PARTIAL
* **Phase 2 (Rescue Registry & Device Identities):** ✅ PASS
* **Phase 3 (Cryptographic Security Layer):** 🟡 PARTIAL

**Overall readiness: 75%**

---

# Phase 1 — Foundation

| Requirement | Status | Evidence | Problems |
| :--- | :---: | :--- | :--- |
| **Project structure** | 🟡 PARTIAL | `backend/app/`, `data/`, `keys/`, `tests/`, `docs/`, `frontend/src/` | `frontend/src` lacks `components/` and `pages/` directories; `frontend/src/App.tsx` is a single 689-line monolithic file. |
| **FastAPI backend** | ✅ PASS | `backend/app/main.py:8-44`, `backend/requirements.txt` | None. App initializes cleanly, registers routes under `/api`, configures CORS and global exception handlers. |
| **React + Vite frontend** | ✅ PASS | `frontend/package.json`, `frontend/vite.config.ts`, builds with `npm run build` | None for build/bundling. |
| **Frontend ↔ backend** | ✅ PASS | `frontend/src/services/api.ts:21-76`, `frontend/src/App.tsx:30-55` | None. Uses `fetch` with `AbortController` timeout, consumes health, system info, registry CRUD, and key provisioning. |
| **Health endpoint** | ✅ PASS | `backend/app/api/routes/health.py:8-14`, `tests/test_health.py` | None. Returns HTTP 200 `{"status": "ok", "service": "RESQ backend", "phase": "phase-3"}`. |
| **Configuration** | ✅ PASS | `backend/app/config.py:8-50`, `.env.example` | None. Pydantic `BaseSettings` handles env vars, CORS parsing, and directory resolution. No secrets hardcoded. |
| **Packet structure** | ❌ FAIL / NOT IMPLEMENTED | `backend/app/models/crypto.py:6-77` | Only `EncryptionEnvelope` exists. There is **no transport packet model** (no `packet_id`, no `sender_id`, no `recipient_id`, no `timestamp`, no sequence/counter, and no signature field). |
| **Security boundaries** | ✅ PASS | `backend/app/services/crypto_service.py:58-62`, `backend/app/models/registry.py:23-29` | Device private keys are kept in `keys/<device_id>/` (filesystem). Registry keeps only public keys. APIs forbid private key egress. |
| **README** | ✅ PASS | `README.md`, `docs/architecture.md` | Fully explains problem, architecture, setup, running instructions, security model, and explicitly states mesh is not yet active. |

---

# Phase 2 — Registry & Identity

| Requirement | Status | Evidence | Problems |
| :--- | :---: | :--- | :--- |
| **Registry** | ✅ PASS | `data/registry.json`, `backend/app/models/registry.py:11-30` | Valid JSON with `version` and `members` array containing Rescue IDs, Device IDs, names, teams, roles, public keys, and statuses. |
| **Rescue IDs** | ✅ PASS | `backend/app/services/registry_service.py:65-88` | Automatically generated in format `RESQ-###`, handling gaps without collision. Tested in `tests/test_registry.py:210-254`. |
| **Device IDs** | ✅ PASS | `backend/app/services/registry_service.py:89-111` | Automatically generated in format `DEVICE-###`, monotonic, collision-safe. |
| **Public keys** | ✅ PASS | `backend/app/models/registry.py:17-18`, `backend/app/services/registry_service.py:200-244` | Stores Base64 raw 32-byte Ed25519 signing public keys and X25519 encryption public keys. Validates exact 32-byte length before storing. |
| **Private key storage** | ✅ PASS | `backend/app/services/crypto_service.py:72-80`, `backend/app/services/crypto_service.py:183-230` | Saved locally as unencrypted PKCS8 PEM at `keys/<device_id>/signing_private.pem` and `encryption_private.pem`. Two-phase atomic staging used during creation. |
| **Member registration** | ✅ PASS | `backend/app/services/registry_service.py:141-170`, `backend/app/api/routes/registry.py:23-35` | Active endpoint `POST /api/registry/members`. Rejects whitespace and client-supplied keys with HTTP 422. Returns 201 with auto-generated IDs. |
| **Registry lookup** | ✅ PASS | `backend/app/services/registry_service.py:118-133`, `backend/app/api/routes/registry.py:38-60` | Supports lookup by `rescue_id` (`GET /api/registry/members/{rescue_id}`) and by `device_id` (`GET /api/registry/devices/{device_id}`). Returns 404 on missing. |
| **Active validation** | 🟡 PARTIAL | `backend/app/services/registry_service.py:134-139`, `backend/app/api/routes/registry.py:62-76` | Function `is_member_active()` is implemented and tested, but `/members/{rescue_id}/status` route inspects `member.status` directly instead of calling the helper. |
| **Revocation** | ✅ PASS | `backend/app/services/registry_service.py:172-198`, `backend/app/api/routes/registry.py:78-101` | `POST /api/registry/members/{rescue_id}/revoke` transitions status to `revoked`, adds UTC timestamp `revoked_at`, preserves historical record. Re-revocation returns 409 Conflict. |
| **Identity generation** | ✅ PASS | `backend/app/services/crypto_service.py:148-238`, `backend/app/api/routes/crypto.py:19-62` | Endpoint `POST /api/crypto/devices/{device_id}/initialize` generates Ed25519 and X25519 pairs, updates registry with public keys, stores private keys on disk. Returns safe public metadata only. |

---

# Phase 3 — Cryptographic Security

| Requirement | Status | Evidence | Problems |
| :--- | :---: | :--- | :--- |
| **`cryptography` library** | ✅ PASS | `backend/app/core/crypto.py:5-9`, `backend/requirements.txt:2` | Uses official `cryptography>=43.0.0` primitives: `ed25519`, `x25519`, `ChaCha20Poly1305`, `HKDF`, `hashes.SHA256`. |
| **Encryption** | ✅ PASS | `backend/app/core/crypto.py:192-245` | Implements Option A: X25519 + ChaCha20-Poly1305 + HKDF-SHA256. |
| **X25519** | ✅ PASS | `backend/app/core/crypto.py:61-65`, `backend/app/core/crypto.py:169-175` | Keypair generation and Diffie-Hellman shared secret exchange (`private_key.exchange(peer_public_key)`). |
| **ChaCha20-Poly1305** | ✅ PASS | `backend/app/core/crypto.py:230-233`, `backend/app/core/crypto.py:280-286` | True AEAD symmetric encryption and decryption with 16-byte Poly1305 authentication tag verification. |
| **Nonce handling** | ✅ PASS | `backend/app/core/crypto.py:213-216`, `tests/test_crypto.py:213-228` | Generates fresh `os.urandom(12)` nonce and fresh `os.urandom(16)` HKDF salt for every encryption. Tests verify nonces are never repeated across identical plaintexts. |
| **Decryption** | ✅ PASS | `backend/app/core/crypto.py:248-287` | Extracts ephemeral key, salt, nonce, ciphertext; re-derives key; binds canonical AAD; decrypts and verifies tag. |
| **Ed25519** | ✅ PASS | `backend/app/core/crypto.py:55-59`, `backend/app/core/crypto.py:137-156` | Pure Ed25519 keypair generation, raw 32-byte public key serialization, and 64-byte signature operations. |
| **Packet signing** | 🟡 PARTIAL | `backend/app/core/crypto.py:137-141`, `backend/app/core/crypto.py:159-167` | `sign_bytes()` and `canonicalize_payload()` exist and are tested. However, **they are not wired into any packet creation or API route**. |
| **Signature verification** | 🟡 PARTIAL | `backend/app/core/crypto.py:143-157` | `verify_signature()` safely returns `False` on any failure. However, **it is not wired into any packet verification or dispatch flow**. |
| **Packet integrity** | 🟡 PARTIAL | `backend/app/core/crypto.py:33-53` | Authenticated Associated Data (AAD) binds the entire envelope header (`version\|key_agreement\|kdf\|cipher\|ephemeral_pub\|salt\|nonce`) plus optional caller AAD. Any tampering causes `DecryptionAuthenticationError`. However, full transport packet integrity is missing because transport packets do not yet exist. |
| **Wrong-key rejection** | ✅ PASS | `backend/app/core/crypto.py:280-286`, `tests/test_crypto.py:288-296` | Decrypting with an incorrect private key raises `DecryptionAuthenticationError`. Verified in unit tests. |
| **Modified-packet rejection** | ✅ PASS | `tests/test_crypto.py:229-286` | Six separate tests confirm that modified ciphertext, modified nonce, modified salt, modified caller AAD, and modified cipher metadata all trigger `DecryptionAuthenticationError`. |
| **Private-key protection** | ✅ PASS | `backend/app/services/crypto_service.py:183-230`, `.gitignore:57-65` | Private keys never cross API or model boundaries. Stored exclusively on disk in `keys/`. Ignored by git. |
| **Error handling** | ✅ PASS | `backend/app/core/crypto.py:13-31`, `backend/app/services/crypto_service.py:30-53` | Clear hierarchy: `CryptoError`, `InvalidKeyTypeError`, `InvalidPublicKeyError`, `DecryptionAuthenticationError`, `InconsistentKeyStateError`, `DeviceAlreadyInitializedError`, `DeviceRevokedError`. |
| **Replay protection** | ❌ NOT IMPLEMENTED | — | **Phase 3 security gap**. The current `EncryptionEnvelope` contains neither a timestamp, sequence counter, message ID, nor a sliding replay window / nonce deduplication cache. |

---

# Security Vulnerabilities

### Vulnerability 1
**Severity:** High  
**Location:** `backend/app/models/crypto.py:6-23` (`EncryptionEnvelope`)  
**Problem:** Absence of replay attack protection (no timestamp, message ID, sequence counter, or nonce cache).  
**Impact:** An attacker who sniffs an encrypted payload on the network can record it and replay it repeatedly to the recipient. The recipient will decrypt the valid envelope each time without knowing it is a replayed message.  
**Recommended fix:** Define a transport `MeshPacket` model that encapsulates `EncryptionEnvelope` alongside `packet_id` (UUIDv4), `sender_device_id`, `recipient_device_id`, `timestamp_utc`, `sequence_num`, and an Ed25519 `signature` over the canonical packet fields. Implement a memory-bounded replay cache tracking recent `packet_id`s within a maximum time window (e.g. 5 minutes).

---

### Vulnerability 2
**Severity:** Medium  
**Location:** `data/registry.json:10-11`  
**Problem:** Pre-seeded member `DEVICE-001` in `data/registry.json` has public keys defined, but no corresponding private keys exist in `keys/DEVICE-001/`.  
**Impact:** `DEVICE-001` is in an unrecoverable inconsistent state out-of-the-box. Calling `crypto_service.check_key_consistency("DEVICE-001")` immediately throws `InconsistentKeyStateError` (HTTP 409). Attempting to load `DEVICE-001`'s private key for signing or decryption fails with `CryptoServiceError`.  
**Recommended fix:** In `data/registry.json`, set `signing_public_key: null` and `encryption_public_key: null` for `RESQ-001`, or provide an initial setup command that generates both the keys and updates the registry cleanly.

---

### Vulnerability 3
**Severity:** Low  
**Location:** `backend/app/services/crypto_service.py:189-190`  
**Problem:** Private keys are stored as unencrypted PKCS8 PEM files on disk without restrictive file permissions (e.g. `chmod 0600` / `stat.S_IRUSR | stat.S_IWUSR`).  
**Impact:** On multi-user POSIX systems, other local users or background processes with read access to the repository directory could read the private key files.  
**Recommended fix:** Explicitly set `os.chmod(path, 0o600)` on the created `.pem` files and `0o700` on the `keys/<device_id>` directory.

---

### Vulnerability 4
**Severity:** Low  
**Location:** `backend/app/config.py:17` & `backend/app/api/routes/system.py:14`  
**Problem:** `encryption_enabled` is set to `False` in default settings and returned as `False` in `/api/system/info`.  
**Impact:** Frontend and external clients querying `/api/system/info` are told `encryption_enabled: false`, conflicting with Phase 3 being active.  
**Recommended fix:** Update `encryption_enabled: bool = True` in `backend/app/config.py` for Phase 3.

---

# Actual Data Flow

Here is the actual data flow currently implemented in the codebase:

```text
User / Administrator (Browser)
   ↓
Frontend UI (React: App.tsx)
   ↓
API Service (services/api.ts)
   ↓  [HTTP / CORS: localhost:8000/api]
FastAPI Router (api_router)
   │
   ├── /api/registry/members (POST/GET)
   │     ↓
   │   RegistryService: Input Validation & ID Generation (RESQ-###, DEVICE-###)
   │     ↓
   │   Atomic JSON Storage (data/registry.json via json_store.py)
   │
   └── /api/crypto/devices/{device_id}/initialize (POST)
         ↓
       CryptoService: Key State & Consistency Check
         ↓
       Core Crypto: generate_ed25519_keypair() & generate_x25519_keypair()
         ↓
       Two-Phase Staging:
         ├─ Step 1: Write private keys to keys/.staging_{device_id}_{uuid}/
         ├─ Step 2: Validate 32-byte public keys & save in data/registry.json
         ├─ Step 3: Move staging dir to keys/{device_id}/
         └─ (On failure: exact rollback of registry public keys)
         ↓
       Returns DeviceCryptoInitResponse (Safe public metadata only)
```

### Flow That Exists Only In Unit Tests (Not Exposed Over Transport/APIs):
```text
Raw Plaintext (bytes)
   ↓
encrypt_authenticated(recipient_x25519_public_key, plaintext, associated_data)
   ├─ Generate fresh ephemeral X25519 keypair
   ├─ Generate fresh random 16-byte HKDF salt
   ├─ X25519 Diffie-Hellman: derive_shared_secret()
   ├─ HKDF-SHA256: derive_encryption_key(shared_secret, salt)
   ├─ Generate fresh random 12-byte nonce
   ├─ AAD Binding: build_envelope_aad(header_params + caller_aad)
   └─ ChaCha20Poly1305.encrypt(nonce, plaintext, aad)
   ↓
EncryptionEnvelope (JSON / Pydantic model)
   ↓
decrypt_authenticated(recipient_x25519_private_key, envelope)
   ├─ Decode ephemeral pub, salt, nonce, ciphertext
   ├─ X25519 Diffie-Hellman + HKDF-SHA256 key derivation
   ├─ Reconstruct identical AAD binding
   └─ ChaCha20Poly1305.decrypt() [Raises DecryptionAuthenticationError if tampered]
   ↓
Verified Plaintext (bytes)
```

### Steps Missing from Current Data Flow:
```text
[MISSING] Sender drafts message
[MISSING] Canonicalization of packet header
[MISSING] Ed25519 Digital Signature over (Header + Ciphertext)
[MISSING] Packet Assembly (Packet ID, Sender, Recipient, Timestamp, Nonce, Envelope, Signature)
[MISSING] Transport Layer / Mesh Transmission (Phase 4/5)
[MISSING] Ingress Packet Signature Verification against Sender's Public Key from Registry
[MISSING] Sender Revocation Check on packet arrival
[MISSING] Replay Window / Cache Verification
[MISSING] Recipient Authorization Check
[MISSING] Delivery to Recipient Inbox UI
```

---

# Files That Matter

1. `backend/app/core/crypto.py`  
   * **Role:** Pure cryptographic primitives. Implements Ed25519 signing/verifying, X25519 key exchange, HKDF-SHA256 key derivation, ChaCha20-Poly1305 authenticated encryption/decryption, and canonical AAD header binding.
2. `backend/app/services/crypto_service.py`  
   * **Role:** Device cryptographic lifecycle manager. Implements two-phase key staging, atomic rollbacks, two-sided disk/registry consistency checks, and local PEM key loading.
3. `backend/app/models/crypto.py`  
   * **Role:** Cryptographic Pydantic schemas. Defines `EncryptionEnvelope` (with strict Base64 byte-length validators), `DeviceCryptoInitResponse`, and `DeviceCryptoStatusResponse`.
4. `backend/app/services/registry_service.py`  
   * **Role:** Member and device registry management. Implements collision-free monotonic ID generation (`RESQ-###`, `DEVICE-###`), registration, revocation lifecycle, and public key persistence.
5. `backend/app/models/registry.py`  
   * **Role:** Registry data contracts. Enforces strict security boundary via `model_validator` forbidding any private key, secret, or seed fields.
6. `backend/app/storage/json_store.py`  
   * **Role:** Safe filesystem persistence. Provides atomic JSON write operations (`NamedTemporaryFile` + `fsync` + `os.replace`).
7. `backend/app/api/routes/crypto.py` & `backend/app/api/routes/registry.py`  
   * **Role:** REST API controllers connecting frontend requests to service operations with proper HTTP status codes.
8. `frontend/src/App.tsx`  
   * **Role:** Frontend UI dashboard for monitoring system status, registering rescue personnel, and triggering cryptographic key provisioning.
9. `tests/test_crypto.py`  
   * **Role:** Comprehensive test suite containing 29 test cases verifying authenticated encryption, tampering rejection, key consistency, and API isolation.

---

# Missing / Incomplete Work

### 🔴 Must fix before demo

1. **Fix Seed Registry Inconsistency for `DEVICE-001`**: Reset `signing_public_key` and `encryption_public_key` to `null` in `data/registry.json` so the pre-seeded member does not throw `InconsistentKeyStateError` (HTTP 409).
2. **Define Unified Transport `MeshPacket` Model**: Create a transport packet model containing:
   * `packet_id`: str (UUIDv4)
   * `sender_device_id`: str
   * `recipient_device_id`: str
   * `timestamp`: str (ISO 8601 UTC)
   * `sequence_num`: int
   * `envelope`: `EncryptionEnvelope`
   * `signature`: str (Ed25519 signature over canonical packet metadata + ciphertext)
3. **Implement Replay Protection**: Add a replay cache mechanism (tracking `packet_id` and timestamp freshness) to reject retransmitted packets.
4. **Implement Packet Signing & Verification Pipeline**: Connect `core/crypto.py`'s `sign_bytes()` and `verify_signature()` to actual messages, validating that the sender's public key exists in the registry and the member is active.

### 🟠 Should fix next

1. **Refactor Frontend Monolith**: Break `frontend/src/App.tsx` into `components/` (`StatusCard`, `MemberForm`, `MemberTable`, `Roadmap`, `MessageForm`) and `pages/`.
2. **Build Message Dispatch & Decryption Endpoints**: Add endpoints (e.g. `/api/messages/send` and `/api/messages/receive`) to demonstrate sending and decrypting real messages in the UI.
3. **Set `encryption_enabled: true` in Config**: Update `encryption_enabled` in `backend/app/config.py` so `/api/system/info` truthfully reflects Phase 3 activation.
4. **Enforce POSIX File Permissions on Private Keys**: Set `0o600` on generated `.pem` files in `backend/app/services/crypto_service.py`.

### 🟢 Optional improvements

1. **Add Cryptographic Self-Test on Startup**: Run a fast ephemeral roundtrip test on server startup to verify hardware/library crypto support.
2. **Add Key Revocation / Rotation Endpoint**: Allow rotating a device's keys if compromised.
3. **Export Public Keystore**: Add an endpoint to export the public registry as a standalone verify-only bundle for offline nodes.

---

# FINAL VERDICT

1. **Are Phase 1 requirements genuinely implemented?**  
   **PARTIALLY.** The FastAPI backend, React/Vite frontend, atomic JSON storage, health endpoints, CORS, and configuration are genuinely implemented. However, the transport packet data structure is not yet modeled, and frontend components/pages are collapsed into a single file.
2. **Are Phase 2 requirements genuinely implemented?**  
   **YES.** The rescue registry, monotonic ID generation, member registration, revocation lifecycle, and public/private key separation are fully implemented, persistent, and tested.
3. **Is Phase 3 cryptography genuinely implemented?**  
   **PARTIALLY.** The core cryptographic primitives (Ed25519 signing/verifying, X25519 key agreement, HKDF-SHA256, ChaCha20-Poly1305 AEAD, and key lifecycle management) are fully implemented and verified with 29 passing tests. However, they are not yet assembled into an end-to-end packet transmission and verification pipeline.
4. **Is the encryption real authenticated encryption?**  
   **YES.** It uses standard ChaCha20-Poly1305 from the Python `cryptography` library with fresh 12-byte nonces, fresh 16-byte HKDF salts, and header-bound Authenticated Associated Data (AAD).
5. **Is Ed25519 signature verification actually working?**  
   **YES.** Key generation, raw byte encoding, signing, and verification are fully functioning and verified by tests. (It is not yet integrated into incoming message handling because messaging is deferred to Phases 4 & 5).
6. **Are private keys protected?**  
   **YES.** Private keys are stored exclusively in local filesystem directories under `keys/`, never committed to Git, never returned by APIs, and strictly barred from `registry.json` by Pydantic model validators.
7. **Can revoked users be rejected?**  
   **YES** for key initialization (returns HTTP 400 `DeviceRevokedError`). Packet-level rejection of revoked senders will occur once the packet verification pipeline is built in Phase 5/6.
8. **Can modified packets be detected?**  
   **YES.** Any tampering with ciphertext, nonce, salt, or header metadata fails Poly1305 authentication and raises `DecryptionAuthenticationError`. Any tampering with signed bytes fails Ed25519 verification.
9. **Can wrong-key decryption be rejected?**  
   **YES.** Decryption with an incorrect X25519 private key raises `DecryptionAuthenticationError`.
10. **Is replay protection implemented?**  
    **NO.** This is an identified security gap in Phase 3. The current envelope contains no timestamp, counter, or replay cache.
11. **Is a real mesh network implemented?**  
    **MESH NETWORK: NOT IMPLEMENTED YET.** The codebase does not implement P2P discovery, multi-hop routing, or packet forwarding. The project documentation and UI explicitly identify this as deferred to Phase 4 ("Software Mesh Simulation").
12. **What exactly should we build next?**  
    * First, fix the seed key inconsistency in `data/registry.json` for `DEVICE-001`.
    * Second, define the unified `MeshPacket` model binding `EncryptionEnvelope` with sender/recipient IDs, timestamp, and an Ed25519 signature.
    * Third, implement replay protection (timestamp freshness check + nonce/packet ID cache).
    * Fourth, proceed to **Phase 4 (Software Mesh Simulation)** to implement peer-to-peer node forwarding before wiring up end-to-end message delivery.
