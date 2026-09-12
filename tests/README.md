# RESQ Test Suite

This directory contains automated tests for the RESQ emergency mesh communication platform.

## Running Tests

From the project root:

```bash
python -m pytest tests/ -v
```

## Test Coverage (47 Tests Total)

### Phase 1: Foundation & Architecture (8 Tests)
- `test_health.py` (2 tests): Health endpoint status, service ID, phase verification, CORS headers.
- `test_system_info.py` (2 tests): Mode, phase, security boundary checks (`encryption_enabled == False`, `mesh_enabled == False`).
- `test_json_store.py` (4 tests): Atomic file operations, nested directory creation, UTF-8 unicode encoding, missing file fallback, malformed JSON error detection.

### Phase 2: Registry & Administrative Device Identities (10 Tests)
- `test_registry.py` (10 tests):
  - Valid registration with auto-generated non-colliding `RESQ-###` and `DEVICE-###` IDs.
  - Multiple registrations generating unique sequence numbers.
  - Lookups by Rescue ID and Device ID, returning 404 for unknown IDs.
  - Whitespace trimming and 422 rejection of empty or whitespace-only inputs.
  - Rejection of malicious payloads containing `private_key` or secret material (`extra="forbid"`).
  - Rejection of client-supplied `signing_public_key` or `encryption_public_key`.
  - Revocation lifecycle: marks `revoked`, sets ISO UTC `revoked_at`, preserves historical record.
  - Rejection of repeated revocation with 409 Conflict.
  - Gap handling in sequential ID generation.
  - Persistence across fresh `RegistryService` instances.
  - Security boundary: no private keys written to disk.

### Phase 3: Cryptographic Security Layer (29 Tests)
- `test_crypto.py` (29 tests):
  - Key Generation: Ed25519 and X25519 keypair generation, raw 32-byte Base64 serialization, PKCS8 PEM serialization.
  - Key Loading Safety: Strict type assertions prevent cross-loading Ed25519 and X25519 PEM files (`InvalidKeyTypeError`).
  - Digital Signatures: Valid signature verification, rejection of tampered data, rejection of corrupted signatures, rejection of wrong public keys.
  - Canonicalization: Insertion-order independent JSON serialization.
  - Key Agreement: X25519 Diffie-Hellman secret derivation between parties, derivation differences across keypairs.
  - Authenticated Encryption: ChaCha20-Poly1305 roundtrip decryption, empty plaintext `b""` support with 16-byte authentication tags.
  - Freshness: Fresh ephemeral key, fresh 16-byte salt, and fresh 12-byte nonce on every encryption.
  - Tamper Detection: Modified ciphertext fails decryption, modified nonce fails decryption, modified salt fails decryption, modified caller AAD fails decryption, modified envelope metadata header fails decryption.
  - Envelope Validation: Pydantic validation rejects malformed Base64, incorrect nonce lengths, and unexpected fields.
  - Key Provisioning Integration: `POST /api/crypto/devices/{device_id}/initialize` updates registry public keys and writes local private keys.
  - Persistence: Public keys persist in `data/registry.json` across fresh reloads.
  - Privacy: Private keys are never returned in API responses.
  - Reinitialization Prevention: Reinitializing already initialized devices returns 409 Conflict.
  - Inconsistency Detection: Two-sided checks detect mismatched local keys vs registry keys and return 409 Conflict.
  - Partial State Detection: Missing keyfiles or missing registry public keys return 409 Conflict with manual recovery required.
  - Negative Initialization: Nonexistent devices return 404; revoked devices return 400.
  - Two-Phase Staging & Rollback: Staging directory failure cleanly restores original registry state.
  - Isolation: Test fixtures isolate keys and registry under `tmp_path`, verifying zero pollution of host storage.
