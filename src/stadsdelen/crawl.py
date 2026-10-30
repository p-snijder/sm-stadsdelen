"""Crawl stadsdeel subsidy overview pages and collect detail URLs."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from stadsdelen.discovery import DistrictPage, SLUG_TO_LABEL, is_district_overview_url
from stadsdelen.http import fetch_text, is_blocked_or_error_page
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


@dataclass(frozen=True)
class DistrictCrawlStats:
    slug: str
    label: str
    pages_fetched: int
    subsidy_links_raw: int
    subsidy_links_unique: int


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


def parse_pagination_next_url(html: str, *, page_url: str) -> str | None:
    """Return the next listing page URL from ``a.startagain``, if present."""
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.select("a.startagain[href]"):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("#"):
            continue
        try:
            return resolve(href, page_url)
        except ValueError:
            continue
    return None


def _district_label(district: DistrictPage) -> str:
    cleaned = district.label.strip()
    if cleaned:
        return cleaned
    return SLUG_TO_LABEL.get(district.slug, district.slug.replace("-", " ").title())


def crawl_district_subsidy_urls(
    district: DistrictPage,
    *,
    client: httpx.Client,
    max_pages: int = 50,
) -> tuple[list[str], DistrictCrawlStats]:
    """Fetch a district overview and pagination pages; dedupe within district."""
    unique: list[str] = []
    seen: set[str] = set()
    raw_count = 0
    pages_fetched = 0
    page_url: str | None = district.url

    while page_url is not None and pages_fetched < max_pages:
        response, text = fetch_text(page_url, client=client)
        pages_fetched += 1
        current_url = str(response.url)
        if is_blocked_or_error_page(response, text):
            msg = (
                f"Blocked or error page when fetching district overview "
                f"(HTTP {response.status_code}): {current_url}"
            )
            raise CrawlError(msg)

        links = parse_subsidy_links(text, page_url=current_url)
        raw_count += len(links)
        for link in links:
            if link not in seen:
                seen.add(link)
                unique.append(link)

        next_url = parse_pagination_next_url(text, page_url=current_url)
        if next_url is None or next_url == current_url:
            break
        page_url = next_url

    stats = DistrictCrawlStats(
        slug=district.slug,
        label=_district_label(district),
        pages_fetched=pages_fetched,
        subsidy_links_raw=raw_count,
        subsidy_links_unique=len(unique),
    )
    return unique, stats
