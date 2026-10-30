"""Crawl stadsdeel subsidy overview pages and collect detail URLs."""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from stadsdelen.discovery import is_district_overview_url
from stadsdelen.urls import CANONICAL_HOST, resolve

NAV_SLUG_DENYLIST = frozenset(
    {
        "niet-meer",
        "subsidies-alfabet",
        "subsidies-onderwerp",
    }
)


class CrawlError(Exception):
    """Raised when crawling cannot produce a usable subsidy index."""


def is_subsidy_detail_url(normalized_url: str) -> bool:
    """Return True for individual subsidy pages, not overview or nav links."""
    parsed = urlparse(normalized_url)
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host.replace("www.", "") != "amsterdam.nl":
        return False
    if host and host not in (CANONICAL_HOST, "amsterdam.nl"):
        return False

    if is_district_overview_url(normalized_url):
        return False

    path = parsed.path or "/"
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2 or segments[0].lower() != "subsidies":
        return False

    if len(segments) == 2 and segments[1].lower() in NAV_SLUG_DENYLIST:
        return False

    if segments[1].lower() == "subsidies-onderwerp":
        return False

    return True


def parse_subsidy_links(html: str, *, page_url: str) -> list[str]:
    """Extract normalized subsidy detail URLs from one listing page."""
    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, None] = {}

    resultaten = soup.select(".resultaten")
    roots = resultaten if resultaten else [soup]

    for root in roots:
        for anchor in root.select(".resultaat h2.link a[href], .resultaat .link a[href]"):
            href = anchor.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            try:
                normalized = resolve(href, page_url)
            except ValueError:
                continue
            if not is_subsidy_detail_url(normalized):
                continue
            seen[normalized] = None

    return list(seen.keys())
