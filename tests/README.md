# RESQ Test Suite

This directory contains automated tests for the RESQ emergency mesh communication platform.

## Running Tests

From the project root:

```bash
python -m pytest tests/ -v
```

## Test Coverage

### Phase 1 Foundation
1. **`test_health.py`**:
   - Validates `GET /api/health` status code, response body, service name, and phase (`phase-2`).
   - Validates CORS response header configuration for development origins (`localhost:5173`).

2. **`test_system_info.py`**:
   - Validates `GET /api/system/info` status code, mode, phase, and flags.
   - Strict boundary verification: ensures `encryption_enabled` and `mesh_enabled` are strictly `False`.

3. **`test_json_store.py`**:
   - Validates `data/registry.json` schema and accessibility.
   - Validates atomic JSON writes and automatic directory creation.
   - Validates UTF-8 encoding support.
   - Validates missing file error handling and default fallback logic.
   - Validates malformed JSON detection and error raising.

### Phase 2 Registry & Device Identities
4. **`test_registry.py`**:
   - Validates member registration with auto-generated non-colliding `rescue_id` (`RESQ-001`) and `device_id` (`DEVICE-001`).
   - Validates that multiple member registrations generate unique sequence numbers.
   - Validates member lookup by Rescue ID and Device ID, returning 404 for unknown IDs.
   - Validates whitespace trimming and 422 rejection of empty or whitespace-only inputs.
   - Validates strict 422 rejection of malicious payloads containing `private_key` or secret materials (`extra="forbid"`).
   - Validates strict 422 rejection of client-supplied `signing_public_key` or `encryption_public_key`.
   - Validates member revocation lifecycle: updates status to `revoked`, sets ISO UTC `revoked_at`, marks `is_active: false`, and retains the historical record.
   - Validates 409 Conflict when attempting to revoke an already revoked member.
   - Validates ID gap handling: if records have `RESQ-001` and `RESQ-003`, next ID is `RESQ-004`.
   - Validates persistence across fresh `RegistryService` instances.
   - Validates security boundary: asserts no private-key fields exist in on-disk JSON records.
   - Strict test isolation: uses `tmp_path` fixture to prevent polluting development `data/registry.json`.
