"""Idempotent Stadsdeel: first-sentence enrichment for subsidy markdown."""

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import Enum

PREFIX_LABEL = "Stadsdeel"

# Leading first sentence only (start of string): Stadsdeel: labels ending with a period.
_LEADING_STADSDEEL = re.compile(
    r"^Stadsdeel:\s*(.+?)\.",
    re.DOTALL,
)


class MarkdownUpdateStatus(str, Enum):
    """Outcome of applying district labels to one markdown field."""

    UPDATED = "updated"
    SKIPPED = "skipped"


def format_stadsdeel_sentence(districts: Sequence[str]) -> str:
    """Return ``Stadsdeel: a, b, c.`` with comma-separated labels."""
    labels = [d.strip() for d in districts if d.strip()]
    if not labels:
        raise ValueError("districts must contain at least one non-empty label")
    joined = ", ".join(labels)
    return f"Stadsdeel: {joined}."


def _split_district_labels(label_text: str) -> tuple[str, ...]:
    parts = [part.strip() for part in label_text.split(",")]
    return tuple(part for part in parts if part)


def parse_leading_stadsdeel(markdown: str) -> tuple[tuple[str, ...] | None, str]:
    """Parse a leading Stadsdeel sentence if present.

    Returns ``(districts, remainder)`` when a prefix is found, else ``(None, markdown)``.
    """
    match = _LEADING_STADSDEEL.match(markdown)
    if match is None:
        return None, markdown
    districts = _split_district_labels(match.group(1))
    remainder = markdown[match.end() :]
    return districts, remainder


def _district_sets_equal(
    existing: tuple[str, ...],
    districts: Sequence[str],
) -> bool:
    new_labels = tuple(d.strip() for d in districts if d.strip())
    return set(existing) == set(new_labels)


def _join_sentence_and_remainder(sentence: str, remainder: str) -> str:
    if not remainder:
        return sentence
    return f"{sentence}\n\n{remainder}"


def update_markdown(
    markdown: str,
    districts: Sequence[str],
) -> tuple[str, MarkdownUpdateStatus]:
    """Prepend or replace the leading Stadsdeel sentence; preserve the body remainder."""
    sentence = format_stadsdeel_sentence(districts)
    existing, remainder = parse_leading_stadsdeel(markdown)

    if existing is not None:
        if _district_sets_equal(existing, districts):
            return markdown, MarkdownUpdateStatus.SKIPPED
        return sentence + remainder, MarkdownUpdateStatus.UPDATED

    return _join_sentence_and_remainder(sentence, markdown), MarkdownUpdateStatus.UPDATED
