"""Load and save versioned UrlToDistrictsIndex cache files."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stadsdelen.index import UrlToDistrictsIndex

CACHE_VERSION = 1


class MapCacheError(Exception):
    """Invalid or unsupported index cache file."""


def load_index_cache(path: str | Path) -> UrlToDistrictsIndex:
    """Read a v1 cache file and return the subsidy URL index."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MapCacheError(f"Cannot read index cache: {file_path}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MapCacheError(
            f"Invalid JSON in index cache {file_path}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise MapCacheError(
            f"Index cache root must be an object, got {type(data).__name__}"
        )

    version = data.get("version")
    if version != CACHE_VERSION:
        raise MapCacheError(
            f"Unsupported index cache version {version!r} "
            f"(expected {CACHE_VERSION})"
        )

    raw_index = data.get("index")
    if raw_index is None:
        raise MapCacheError("Index cache missing required key 'index'")
    return _parse_index(raw_index, source=str(file_path))


def _parse_index(raw_index: object, *, source: str) -> UrlToDistrictsIndex:
    if not isinstance(raw_index, dict):
        raise MapCacheError(
            f"Index cache 'index' must be an object, got {type(raw_index).__name__}"
        )

    result: UrlToDistrictsIndex = {}
    for url, labels in raw_index.items():
        if not isinstance(url, str) or not url.strip():
            raise MapCacheError(f"Index cache keys must be non-empty strings ({source})")
        if not isinstance(labels, list):
            raise MapCacheError(
                f"Index entry for {url!r} must be a list of labels ({source})"
            )
        cleaned_labels: list[str] = []
        for label in labels:
            if not isinstance(label, str) or not label.strip():
                raise MapCacheError(
                    f"Index entry for {url!r} contains invalid label ({source})"
                )
            cleaned_labels.append(label.strip())
        if not cleaned_labels:
            raise MapCacheError(
                f"Index entry for {url!r} must have at least one label ({source})"
            )
        result[url] = cleaned_labels
    return result


def save_index_cache(
    path: str | Path,
    index: UrlToDistrictsIndex,
    *,
    entry_url: str | None = None,
) -> None:
    """Write ``index`` to ``path`` atomically as cache version 1."""
    file_path = Path(path)
    payload: dict[str, Any] = {
        "version": CACHE_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "index": dict(sorted(index.items())),
    }
    if entry_url is not None:
        payload["entry_url"] = entry_url

    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        temp_path.write_text(text, encoding="utf-8")
        os.replace(temp_path, file_path)
    except OSError as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise MapCacheError(f"Cannot write index cache: {file_path}") from exc
