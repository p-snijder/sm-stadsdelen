from stadsdelen.crawl import CrawlReport, DistrictCrawlStats
from stadsdelen.reporting import (
    EnrichResult,
    MatchResult,
    UnmatchedRow,
    format_crawl_report,
    format_enrich_report,
    format_enrich_run_summary,
    format_match_report,
)


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


def test_format_crawl_report_includes_districts_and_failures() -> None:
    report = CrawlReport(
        by_district=(
            DistrictCrawlStats(
                slug="centrum",
                label="Subsidies Centrum",
                pages_fetched=1,
                subsidy_links_raw=3,
                subsidy_links_unique=3,
            ),
            DistrictCrawlStats(
                slug="noord",
                label="Subsidies Noord",
                pages_fetched=2,
                subsidy_links_raw=4,
                subsidy_links_unique=2,
            ),
        ),
        index_size=4,
        http_failures=("https://www.amsterdam.nl/subsidies/noord: blocked",),
    )
    text = format_crawl_report(report)
    assert "Districts crawled: 2" in text
    assert "Subsidy URLs indexed: 4" in text
    assert "Subsidies Centrum: 3 unique links" in text
    assert "Subsidies Noord: 2 unique links (2 page(s))" in text
    assert "HTTP failures:" in text
    assert "noord: blocked" in text


def test_format_enrich_run_summary_dry_run_footer() -> None:
    crawl = CrawlReport(by_district=(), index_size=0, http_failures=())
    match = MatchResult(matched=(), unmatched=(), total_rows=0)
    enrich = EnrichResult(updated=0, skipped=0, matched=0)
    text = format_enrich_run_summary(
        crawl=crawl,
        match=match,
        enrich=enrich,
        dry_run=True,
        wrote_file=False,
    )
    assert "Dry run: no file written." in text
    assert "Districts crawled: 0" in text


def test_format_enrich_report_includes_counts() -> None:
    result = EnrichResult(updated=2, skipped=0, matched=2)
    text = format_enrich_report(result)
    assert "Matched rows enriched: 2" in text
    assert "Markdown updated: 2" in text
    assert "Markdown skipped (already correct): 0" in text
    assert text.endswith("\n")
