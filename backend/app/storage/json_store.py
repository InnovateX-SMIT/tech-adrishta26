import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union


class JsonStoreError(Exception):
    """Base exception for JSON storage operations."""
    pass


class FileNotFoundStoreError(JsonStoreError):
    """Raised when the specified JSON storage file does not exist."""
    pass


class InvalidJsonStoreError(JsonStoreError):
    """Raised when the JSON storage file contains malformed or unparseable JSON."""
    pass


def load_json(file_path: Union[str, Path], default: Optional[Any] = None) -> Any:
    """Safely load and parse JSON from the filesystem.

    Args:
        file_path: Path to the JSON file.
        default: Fallback value returned if the file does not exist.
                 If default is None and the file is missing, FileNotFoundStoreError is raised.

    Returns:
        Parsed JSON data (dict, list, etc.).

    Raises:
        FileNotFoundStoreError: If file is missing and default is None.
        InvalidJsonStoreError: If file content is not valid JSON.
        JsonStoreError: If an I/O error occurs during reading.
    """
    path = Path(file_path).resolve()

    if not path.is_file():
        if default is not None:
            return default
        raise FileNotFoundStoreError(f"JSON store file not found: {path}")

    try:
        with open(path, mode="r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise InvalidJsonStoreError(
            f"Invalid JSON in store file {path} at line {exc.lineno}, col {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise JsonStoreError(f"I/O error reading JSON store file {path}: {exc}") from exc


def save_json(file_path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """Safely and atomically write JSON data to the filesystem.

    Ensures parent directories exist, writes to a temporary file in the same
    directory, flushes to disk, and replaces the target file atomically.

    Args:
        file_path: Target path for the JSON file.
        data: JSON-serializable data to persist.
        indent: Indentation level for readability (default: 2).

    Raises:
        JsonStoreError: If serializing or writing to disk fails.
    """
    path = Path(file_path).resolve()
    parent_dir = path.parent

    try:
        parent_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise JsonStoreError(f"Failed to create directory {parent_dir}: {exc}") from exc

    temp_path: Optional[Path] = None
    try:
        # Create temporary file in the same directory to allow atomic os.replace across filesystem boundaries
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=parent_dir,
            delete=False,
            suffix=".tmp"
        ) as tmp_file:
            temp_path = Path(tmp_file.name)
            json.dump(data, tmp_file, indent=indent, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # Atomic replacement of target file
        os.replace(temp_path, path)
        temp_path = None
    except (TypeError, ValueError) as exc:
        raise JsonStoreError(f"Data is not JSON serializable: {exc}") from exc
    except OSError as exc:
        raise JsonStoreError(f"Failed to write JSON store file {path}: {exc}") from exc
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
