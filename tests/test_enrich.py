import copy
from pathlib import Path

from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.json_io import load_subsidy_array
from stadsdelen.markdown import enrich_subsidies

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
)


def test_enrich_subsidies_updates_matched_rows_only(
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    records = load_subsidy_array(FIXTURE)
    original = copy.deepcopy(records)

    _, enrich_first = enrich_subsidies(records, sample_match_index)
    assert enrich_first.matched == 2
    assert enrich_first.updated == 2
    assert enrich_first.skipped == 0

    assert records[0]["markdown"] == (
        "Stadsdeel: Subsidies Centrum, Subsidies Noord.\n\nFirst body paragraph."
    )
    assert records[1]["markdown"] == (
        "Stadsdeel: Subsidies Centrum.\n\nCentrum-only body."
    )
    assert records[2]["markdown"] == original[2]["markdown"]
    assert records[3]["markdown"] == original[3]["markdown"]
    assert records[0]["id"] == "row-1"
    assert records[0]["title"] == "Shared city-wide regeling"
    assert records[0]["url"] == original[0]["url"]


def test_enrich_subsidies_second_run_is_idempotent(
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    records = load_subsidy_array(FIXTURE)
    enrich_subsidies(records, sample_match_index)
    after_first = copy.deepcopy(records)

    _, enrich_second = enrich_subsidies(records, sample_match_index)
    assert enrich_second.matched == 2
    assert enrich_second.updated == 0
    assert enrich_second.skipped == 2
    assert records == after_first
