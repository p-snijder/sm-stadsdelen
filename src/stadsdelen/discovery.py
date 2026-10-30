"""Discover stadsdeel subsidy overview pages from the entry URL."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from stadsdelen.urls import CANONICAL_HOST, resolve

SLUG_DENYLIST = frozenset(
    {
        "",
        "subsidies",
        "subsidies-onderwerp",
    }
)

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
        slug = _district_slug_from_url(normalized)
        if slug is None:
            continue
        label = _label_from_anchor(anchor.get_text(), slug)
        page = DistrictPage(slug=slug, label=label, url=normalized)
        by_url[normalized] = page

    return sorted(by_url.values(), key=lambda item: item.slug)


def _district_slug_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname and parsed.hostname.lower().replace("www.", "") != "amsterdam.nl":
        return None
    if parsed.hostname and parsed.hostname.lower() not in (
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
