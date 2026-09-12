# RESQ Test Suite

This directory contains automated tests for the RESQ emergency mesh communication platform.

## Running Tests

From the project root:

```bash
python -m pytest tests/ -v
```

## Test Coverage (Phase 1)

1. **`test_health.py`**:
   - Validates `GET /api/health` status code, response body, service name, and phase.
   - Validates CORS response header configuration for development origins.

2. **`test_system_info.py`**:
   - Validates `GET /api/system/info` status code, mode, phase, and flags.
   - Strict boundary verification: ensures `encryption_enabled` and `mesh_enabled` are strictly `False` in Phase 1.

3. **`test_json_store.py`**:
   - Validates `data/registry.json` schema and accessibility.
   - Validates atomic JSON writes and automatic directory creation.
   - Validates UTF-8 encoding support.
   - Validates missing file error handling and default fallback logic.
   - Validates malformed JSON detection and error raising.
