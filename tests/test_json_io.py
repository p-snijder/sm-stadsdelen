from pathlib import Path

import pytest

from stadsdelen.json_io import (
    JsonLoadError,
    load_subsidy_array,
    load_subsidy_array_from_text,
)

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
)


def test_load_subsidy_array_from_fixture_preserves_extra_fields() -> None:
    records = load_subsidy_array(FIXTURE)
    assert len(records) == 4
    assert records[0]["id"] == "row-1"
    assert records[0]["title"] == "Shared city-wide regeling"
    assert records[0]["url"].startswith("https://")


def test_load_subsidy_array_from_text_valid() -> None:
    text = '[{"url": "https://example.com/a", "markdown": "x"}]'
    assert load_subsidy_array_from_text(text) == [
        {"url": "https://example.com/a", "markdown": "x"},
    ]


def test_load_subsidy_array_rejects_non_array_root() -> None:
    with pytest.raises(JsonLoadError, match="JSON root must be an array"):
        load_subsidy_array_from_text('{"url": "x", "markdown": "y"}')


def test_load_subsidy_array_rejects_invalid_json() -> None:
    with pytest.raises(JsonLoadError, match="Invalid JSON"):
        load_subsidy_array_from_text("{not json")


def test_load_subsidy_array_rejects_non_object_element() -> None:
    with pytest.raises(JsonLoadError, match="index 1 must be an object"):
        load_subsidy_array_from_text('[{"url": "a", "markdown": "b"}, "nope"]')


def test_load_subsidy_array_rejects_missing_url() -> None:
    with pytest.raises(JsonLoadError, match="index 0 missing required key 'url'"):
        load_subsidy_array_from_text('[{"markdown": "only"}]')


def test_load_subsidy_array_rejects_missing_markdown() -> None:
    with pytest.raises(JsonLoadError, match="index 0 missing required key 'markdown'"):
        load_subsidy_array_from_text('[{"url": "https://example.com"}]')


def test_load_subsidy_array_rejects_non_string_url() -> None:
    with pytest.raises(JsonLoadError, match="'url' must be a string"):
        load_subsidy_array_from_text('[{"url": 42, "markdown": "x"}]')


def test_load_subsidy_array_rejects_non_string_markdown() -> None:
    with pytest.raises(JsonLoadError, match="'markdown' must be a string"):
        load_subsidy_array_from_text(
            '[{"url": "https://example.com", "markdown": null}]'
        )


def test_load_subsidy_array_missing_file() -> None:
    with pytest.raises(JsonLoadError, match="Cannot read JSON file"):
        load_subsidy_array("/nonexistent/subsidies.json")
