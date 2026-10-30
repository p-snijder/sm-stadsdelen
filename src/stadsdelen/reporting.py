"""Match and crawl reporting types and formatters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatchedRow:
    """One JSON array row whose URL exists in the subsidy index."""

    index: int
    url: str
    normalized_url: str
    districts: tuple[str, ...]


@dataclass(frozen=True)
class UnmatchedRow:
    """One JSON array row that could not be matched to the index."""

    index: int
    url: str
    normalized_url: str
    reason: str


@dataclass(frozen=True)
class MatchResult:
    """Outcome of matching a subsidy JSON array against UrlToDistrictsIndex."""

    matched: tuple[MatchedRow, ...]
    unmatched: tuple[UnmatchedRow, ...]
    total_rows: int

    @property
    def matched_count(self) -> int:
        return len(self.matched)

    @property
    def unmatched_count(self) -> int:
        return len(self.unmatched)


@dataclass(frozen=True)
class EnrichResult:
    """Counts from applying Stadsdeel markdown updates to matched rows."""

    updated: int
    skipped: int
    matched: int


def format_enrich_report(result: EnrichResult) -> str:
    """Human-readable summary of markdown enrichment counts."""
    lines = [
        f"Matched rows enriched: {result.matched}",
        f"Markdown updated: {result.updated}",
        f"Markdown skipped (already correct): {result.skipped}",
    ]
    return "\n".join(lines) + "\n"


def format_match_report(result: MatchResult) -> str:
    """Human-readable summary for dry-run output."""
    lines = [
        f"JSON rows: {result.total_rows}",
        f"Matched: {result.matched_count}",
        f"Unmatched: {result.unmatched_count}",
    ]
    if result.unmatched:
        lines.append("Unmatched URLs:")
        for row in sorted(result.unmatched, key=lambda r: r.index):
            if row.normalized_url:
                lines.append(
                    f"  [{row.index}] {row.url} -> {row.normalized_url} ({row.reason})"
                )
            else:
                lines.append(f"  [{row.index}] {row.url} ({row.reason})")
    return "\n".join(lines) + "\n"
