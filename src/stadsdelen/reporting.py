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
