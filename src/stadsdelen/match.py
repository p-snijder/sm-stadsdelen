"""Match subsidy JSON records against a UrlToDistrictsIndex."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.json_io import load_subsidy_array
from stadsdelen.reporting import MatchedRow, MatchResult, UnmatchedRow
from stadsdelen.urls import normalize

REASON_NOT_IN_INDEX = "not_in_index"
REASON_NORMALIZE_FAILED = "normalize_failed"


def match_subsidies(
    records: list[dict[str, Any]],
    index: UrlToDistrictsIndex,
) -> MatchResult:
    """Match by normalized url without mutating records."""
    matched: list[MatchedRow] = []
    unmatched: list[UnmatchedRow] = []

    for row_index, record in enumerate(records):
        url = record["url"]
        try:
            normalized_url = normalize(url)
        except ValueError:
            unmatched.append(
                UnmatchedRow(
                    index=row_index,
                    url=url,
                    normalized_url="",
                    reason=REASON_NORMALIZE_FAILED,
                )
            )
            continue

        labels = index.get(normalized_url)
        if labels is None:
            unmatched.append(
                UnmatchedRow(
                    index=row_index,
                    url=url,
                    normalized_url=normalized_url,
                    reason=REASON_NOT_IN_INDEX,
                )
            )
            continue

        matched.append(
            MatchedRow(
                index=row_index,
                url=url,
                normalized_url=normalized_url,
                districts=tuple(labels),
            )
        )

    return MatchResult(
        matched=tuple(matched),
        unmatched=tuple(unmatched),
        total_rows=len(records),
    )


def match_subsidies_file(
    json_path: str | Path,
    index: UrlToDistrictsIndex,
) -> tuple[list[dict[str, Any]], MatchResult]:
    """Load a JSON array from disk and match against ``index``."""
    records = load_subsidy_array(json_path)
    return records, match_subsidies(records, index)
