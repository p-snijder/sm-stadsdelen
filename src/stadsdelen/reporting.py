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
