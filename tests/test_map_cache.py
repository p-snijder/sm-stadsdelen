import json
from pathlib import Path

import pytest

from stadsdelen.map_cache import (
    CACHE_VERSION,
    MapCacheError,
    load_index_cache,
    save_index_cache,
)

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidy-index-v1.json"
)


def test_load_fixture_matches_sample_index(sample_match_index) -> None:
    loaded = load_index_cache(FIXTURE)
    assert loaded == sample_match_index


def test_save_and_load_round_trip(tmp_path: Path, sample_match_index) -> None:
    target = tmp_path / "cache.json"
    entry = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"
    save_index_cache(target, sample_match_index, entry_url=entry)
    loaded = load_index_cache(target)
    assert loaded == sample_match_index
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["version"] == CACHE_VERSION
    assert data["entry_url"] == entry
    assert "generated_at" in data


def test_load_rejects_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "bad-version.json"
    path.write_text(
        json.dumps({"version": 99, "index": {}}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(MapCacheError, match="Unsupported index cache version"):
        load_index_cache(path)


def test_load_rejects_malformed_index(tmp_path: Path) -> None:
    path = tmp_path / "bad-index.json"
    path.write_text(
        json.dumps({"version": 1, "index": "not-a-dict"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(MapCacheError, match="'index' must be an object"):
        load_index_cache(path)


def test_load_rejects_empty_label_list(tmp_path: Path) -> None:
    path = tmp_path / "empty-labels.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "index": {"https://www.amsterdam.nl/subsidies/foo": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(MapCacheError, match="at least one label"):
        load_index_cache(path)
