from pathlib import Path
import pytest
from backend.app.storage.json_store import (
    load_json,
    save_json,
    FileNotFoundStoreError,
    InvalidJsonStoreError,
)


def test_registry_file_exists_and_valid():
    registry_path = Path("data/registry.json")
    assert registry_path.is_file()
    data = load_json(registry_path)
    assert isinstance(data, dict)
    assert data["version"] == 1
    assert "members" in data
    assert isinstance(data["members"], list)


def test_save_and_load_json_roundtrip(tmp_path: Path):
    target_file = tmp_path / "nested" / "dir" / "test_data.json"
    payload = {
        "network": "RESQ-MESH",
        "node_count": 5,
        "active": True,
        "unicode_notes": "Emergência 🚨 救援",
    }

    # Should create nested parent dirs automatically
    save_json(target_file, payload)
    assert target_file.is_file()

    loaded = load_json(target_file)
    assert loaded == payload
    assert loaded["unicode_notes"] == "Emergência 🚨 救援"


def test_load_missing_file_raises_or_returns_default(tmp_path: Path):
    missing_file = tmp_path / "non_existent.json"

    # With default provided, returns default
    assert load_json(missing_file, default={"fallback": True}) == {"fallback": True}

    # Without default, raises FileNotFoundStoreError
    with pytest.raises(FileNotFoundStoreError) as exc_info:
        load_json(missing_file)
    assert "not found" in str(exc_info.value).lower()


def test_load_malformed_json_raises_invalid_json_store_error(tmp_path: Path):
    broken_file = tmp_path / "corrupt.json"
    broken_file.write_text("{ unquoted_key: invalid JSON ...", encoding="utf-8")

    with pytest.raises(InvalidJsonStoreError) as exc_info:
        load_json(broken_file)
    assert "Invalid JSON in store file" in str(exc_info.value)
