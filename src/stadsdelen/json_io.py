"""Load and validate user subsidy JSON arrays."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


class JsonLoadError(Exception):
    """Invalid file, non-array root, or row missing required fields."""


class JsonSaveError(Exception):
    """Backup or atomic write failed; original file must remain intact."""


def load_subsidy_array(path: str | Path) -> list[dict[str, Any]]:
    """Read UTF-8 JSON from ``path`` and validate a subsidy record array."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JsonLoadError(f"Cannot read JSON file: {file_path}") from exc
    return load_subsidy_array_from_text(text, source=str(file_path))


def load_subsidy_array_from_text(
    text: str,
    *,
    source: str = "<string>",
) -> list[dict[str, Any]]:
    """Parse and validate JSON text as an array of subsidy objects."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise JsonLoadError(f"Invalid JSON in {source}: {exc.msg}") from exc

    if not isinstance(data, list):
        raise JsonLoadError(f"JSON root must be an array, got {type(data).__name__}")

    records: list[dict[str, Any]] = []
    for index, element in enumerate(data):
        if not isinstance(element, dict):
            raise JsonLoadError(
                f"Array element at index {index} must be an object, "
                f"got {type(element).__name__}"
            )
        _validate_record_fields(element, index)
        records.append(element)
    return records


def _validate_record_fields(record: dict[str, Any], index: int) -> None:
    for key in ("url", "markdown"):
        if key not in record:
            raise JsonLoadError(
                f"Array element at index {index} missing required key {key!r}"
            )
        value = record[key]
        if not isinstance(value, str):
            raise JsonLoadError(
                f"Array element at index {index}: {key!r} must be a string, "
                f"got {type(value).__name__}"
            )


def save_subsidy_array(
    path: str | Path,
    records: list[dict[str, Any]],
    *,
    backup: bool = True,
) -> Path | None:
    """Write ``records`` to ``path`` atomically with optional ``.bak`` backup."""
    file_path = Path(path)
    backup_path: Path | None = None

    if backup and file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        try:
            shutil.copy2(file_path, backup_path)
        except OSError as exc:
            raise JsonSaveError(f"Cannot create backup at {backup_path}") from exc

    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        payload = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, file_path)
    except OSError as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise JsonSaveError(f"Cannot write JSON file: {file_path}") from exc

    return backup_path
