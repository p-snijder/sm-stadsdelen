from pathlib import Path

from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.match import (
    REASON_NORMALIZE_FAILED,
    REASON_NOT_IN_INDEX,
    match_subsidies,
    match_subsidies_file,
)

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
)


def test_match_subsidies_file_on_sample_fixture(
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    records, result = match_subsidies_file(FIXTURE, sample_match_index)
    assert len(records) == 4
    assert result.total_rows == 4
    assert result.matched_count == 2
    assert result.unmatched_count == 2

    shared = result.matched[0]
    assert shared.index == 0
    assert (
        shared.normalized_url == "https://www.amsterdam.nl/subsidies/city-wide-regeling"
    )
    assert shared.districts == ("Subsidies Centrum", "Subsidies Noord")

    centrum = result.matched[1]
    assert centrum.index == 1
    assert centrum.normalized_url == (
        "https://www.amsterdam.nl/subsidies/bewonersinitiatieven-centrum"
    )
    assert centrum.districts == ("Subsidies Centrum",)

    not_in_index = next(r for r in result.unmatched if r.reason == REASON_NOT_IN_INDEX)
    assert not_in_index.index == 2
    assert (
        not_in_index.normalized_url
        == "https://www.amsterdam.nl/subsidies/unknown-regeling"
    )

    normalize_failed = next(
        r for r in result.unmatched if r.reason == REASON_NORMALIZE_FAILED
    )
    assert normalize_failed.index == 3
    assert normalize_failed.url == "not-a-valid-url"
    assert normalize_failed.normalized_url == ""


def test_match_subsidies_does_not_mutate_records(
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    records = [
        {
            "id": "a",
            "url": "https://www.amsterdam.nl/subsidies/city-wide-regeling",
            "markdown": "m",
        },
    ]
    original = records[0].copy()
    match_subsidies(records, sample_match_index)
    assert records[0] == original


def test_match_subsidies_empty_index_marks_all_not_in_index() -> None:
    records = [{"url": "https://www.amsterdam.nl/subsidies/foo", "markdown": "x"}]
    result = match_subsidies(records, {})
    assert result.matched_count == 0
    assert result.unmatched_count == 1
    assert result.unmatched[0].reason == REASON_NOT_IN_INDEX


def test_match_subsidies_duplicate_urls_matched_independently(
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    url = "https://www.amsterdam.nl/subsidies/city-wide-regeling"
    records = [
        {"url": url, "markdown": "one"},
        {"url": url + "/", "markdown": "two"},
    ]
    result = match_subsidies(records, sample_match_index)
    assert result.matched_count == 2
    assert result.matched[0].index == 0
    assert result.matched[1].index == 1
