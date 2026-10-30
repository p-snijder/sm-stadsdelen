"""Merge subsidy URLs from multiple stadsdeel listings into one index."""

from __future__ import annotations

import locale
from collections import defaultdict
from typing import TypeAlias

from stadsdelen.discovery import normalize_district_label

UrlToDistrictsIndex: TypeAlias = dict[str, list[str]]


def _sort_labels(labels: set[str]) -> list[str]:
    try:
        locale.setlocale(locale.LC_COLLATE, "nl_NL.UTF-8")
        return sorted(labels, key=locale.strxfrm)
    except locale.Error:
        try:
            locale.setlocale(locale.LC_COLLATE, "nl_NL")
            return sorted(labels, key=locale.strxfrm)
        except locale.Error:
            return sorted(labels)


class IndexBuilder:
    """Accumulate normalized subsidy URLs with stadsdeel labels."""

    def __init__(self) -> None:
        self._labels_by_url: dict[str, set[str]] = defaultdict(set)

    def add_district_urls(self, urls: list[str], label: str) -> None:
        """Associate ``label`` with each normalized subsidy URL."""
        cleaned = normalize_district_label(label.strip())
        if not cleaned:
            return
        for url in urls:
            self._labels_by_url[url].add(cleaned)

    def finalize(self) -> UrlToDistrictsIndex:
        """Return immutable index with alphabetically sorted label lists."""
        return {
            url: _sort_labels(labels)
            for url, labels in sorted(self._labels_by_url.items())
        }
