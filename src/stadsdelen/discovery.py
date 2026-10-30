"""Discover stadsdeel subsidy overview pages from the entry URL."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from stadsdelen.http import create_client, is_blocked_or_error_page, warm_session
from stadsdelen.urls import CANONICAL_HOST, normalize, resolve

DEFAULT_ENTRY_URL = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"

WARMUP_URLS = (
    "https://www.amsterdam.nl/",
    "https://www.amsterdam.nl/subsidies/",
)

FALLBACK_ENV_VAR = "STADSDELEN_DISTRICT_FALLBACK"

SLUG_DENYLIST = frozenset(
    {
        "",
        "subsidies",
        "subsidies-onderwerp",
    }
)

DISTRICT_OVERVIEW_SLUGS = frozenset(
    {
        "centrum",
        "nieuwwest",
        "noord",
        "oost",
        "subsidies-stadsgebied-weesp",
        "west",
        "zuid",
        "zuidoost",
    }
)

CANONICAL_SLUG: dict[str, str] = {
    "subsidies-stadsgebied-weesp": "weesp",
}

SLUG_TO_LABEL: dict[str, str] = {
    "centrum": "Centrum",
    "noord": "Noord",
    "oost": "Oost",
    "west": "West",
    "zuid": "Zuid",
    "zuidoost": "Zuidoost",
    "nieuwwest": "Nieuw-West",
    "weesp": "Weesp",
}

DEFAULT_DISTRICT_OVERVIEW_PATHS: tuple[str, ...] = (
    "/subsidies/centrum/",
    "/subsidies/nieuwwest/",
    "/subsidies/noord/",
    "/subsidies/oost/",
    "/subsidies/subsidies-stadsgebied-weesp/",
    "/subsidies/west/",
    "/subsidies/zuid/",
    "/subsidies/zuidoost/",
)


@dataclass(frozen=True)
class DistrictPage:
    slug: str
    label: str
    url: str


class DiscoveryError(Exception):
    """Raised when district overview pages cannot be discovered."""


def parse_district_pages(html: str, *, page_url: str) -> list[DistrictPage]:
    """Extract stadsdeel overview links from HTML without performing HTTP."""
    soup = BeautifulSoup(html, "html.parser")
    by_url: dict[str, DistrictPage] = {}

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        try:
            normalized = resolve(href, page_url)
        except ValueError:
            continue
        path_slug = _district_slug_from_url(normalized)
        if path_slug is None or path_slug not in DISTRICT_OVERVIEW_SLUGS:
            continue
        slug = CANONICAL_SLUG.get(path_slug, path_slug)
        label = _label_from_anchor(anchor.get_text(), slug)
        page = DistrictPage(slug=slug, label=label, url=normalized)
        by_url[normalized] = page

    return sorted(by_url.values(), key=lambda item: item.slug)


def discover_district_pages(
    entry_url: str,
    *,
    client: httpx.Client | None = None,
    min_districts: int = 7,
    allow_fallback: bool | None = None,
) -> list[DistrictPage]:
    """Fetch the entry page and return stadsdeel subsidy overview links."""
    own_client = client is None
    http = client if client is not None else create_client(timeout=30.0)
    try:
        if own_client:
            warm_session(http, WARMUP_URLS)
        response = http.get(entry_url)
        text = response.text
        if is_blocked_or_error_page(response, text):
            msg = (
                f"Blocked or error page when fetching entry URL "
                f"(HTTP {response.status_code}): {entry_url}"
            )
            raise DiscoveryError(msg)

        pages = parse_district_pages(text, page_url=str(response.url))
        if len(pages) < min_districts and _fallback_enabled(allow_fallback):
            pages = fallback_district_pages(entry_url)

        if len(pages) < min_districts:
            raise DiscoveryError(
                f"Expected at least {min_districts} district overview pages, "
                f"found {len(pages)} on {entry_url}"
            )
        return pages
    finally:
        if own_client:
            http.close()


def fallback_district_pages(entry_url: str) -> list[DistrictPage]:
    """Return the canonical district overview list without parsing HTML."""
    base = normalize(entry_url)
    pages: list[DistrictPage] = []
    for path in DEFAULT_DISTRICT_OVERVIEW_PATHS:
        url = resolve(path, base)
        path_slug = _district_slug_from_url(url)
        if path_slug is None or path_slug not in DISTRICT_OVERVIEW_SLUGS:
            continue
        slug = CANONICAL_SLUG.get(path_slug, path_slug)
        pages.append(
            DistrictPage(
                slug=slug,
                label=SLUG_TO_LABEL.get(slug, slug.replace("-", " ").title()),
                url=url,
            )
        )
    return sorted(pages, key=lambda item: item.slug)


def _fallback_enabled(allow_fallback: bool | None) -> bool:
    if allow_fallback is not None:
        return allow_fallback
    return os.environ.get(FALLBACK_ENV_VAR, "").strip() in {"1", "true", "yes"}


def _district_slug_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host and host.replace("www.", "") != "amsterdam.nl":
        return None
    if host and host not in (
        CANONICAL_HOST,
        "amsterdam.nl",
    ):
        return None

    path = parsed.path or "/"
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) != 2 or segments[0].lower() != "subsidies":
        return None

    slug = segments[1].lower()
    if slug in SLUG_DENYLIST:
        return None
    return slug


def _label_from_anchor(text: str, slug: str) -> str:
    cleaned = " ".join(text.split())
    if cleaned and cleaned.lower() not in {"lees meer", "meer info", "subsidies"}:
        return cleaned
    return SLUG_TO_LABEL.get(slug, slug.replace("-", " ").title())
