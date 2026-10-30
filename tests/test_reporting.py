from stadsdelen.reporting import MatchResult, UnmatchedRow, EnrichResult, format_enrich_report, format_match_report


def test_format_match_report_includes_totals_and_unmatched() -> None:
    result = MatchResult(
        matched=(),
        unmatched=(
            UnmatchedRow(
                index=2,
                url="https://www.amsterdam.nl/subsidies/unknown-regeling",
                normalized_url="https://www.amsterdam.nl/subsidies/unknown-regeling",
                reason="not_in_index",
            ),
            UnmatchedRow(
                index=3,
                url="not-a-valid-url",
                normalized_url="",
                reason="normalize_failed",
            ),
        ),
        total_rows=4,
    )
    text = format_match_report(result)
    assert "JSON rows: 4" in text
    assert "Matched: 0" in text
    assert "Unmatched: 2" in text
    assert "unknown-regeling" in text
    assert "normalize_failed" in text
    assert text.endswith("\n")


def test_format_enrich_report_includes_counts() -> None:
    result = EnrichResult(updated=2, skipped=0, matched=2)
    text = format_enrich_report(result)
    assert "Matched rows enriched: 2" in text
    assert "Markdown updated: 2" in text
    assert "Markdown skipped (already correct): 0" in text
    assert text.endswith("\n")
