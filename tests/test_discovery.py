from pathlib import Path

import pytest

from stadsdelen.discovery import (
    DiscoveryError,
    DistrictPage,
    discover_district_pages,
    is_district_overview_url,
    parse_district_pages,
)
from stadsdelen.http import ERROR_PAGE_TITLE_FRAGMENT, create_client

ENTRY = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "html"


def test_is_district_overview_url() -> None:
    assert is_district_overview_url("https://www.amsterdam.nl/subsidies/centrum")
    assert is_district_overview_url("https://www.amsterdam.nl/subsidies/zuidoost/")
    assert not is_district_overview_url(
        "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/foo"
    )
    assert not is_district_overview_url(
        "https://www.amsterdam.nl/subsidies/bewonersinitiatieven-centrum"
    )


def test_parse_district_pages_finds_relative_and_absolute_links() -> None:
    html = """
    <html><body>
      <a href="/subsidies/centrum/">Centrum</a>
      <a href="https://www.amsterdam.nl/subsidies/noord/">Noord</a>
      <a href="/subsidies/subsidies-onderwerp/">Onderwerp</a>
      <a href="/subsidies/centrum/foo/">Detail</a>
    </body></html>
    """
    pages = parse_district_pages(html, page_url=ENTRY)
    assert pages == [
        DistrictPage(
            slug="centrum",
            label="Centrum",
            url="https://www.amsterdam.nl/subsidies/centrum",
        ),
        DistrictPage(
            slug="noord",
            label="Noord",
            url="https://www.amsterdam.nl/subsidies/noord",
        ),
    ]


def test_parse_district_pages_dedupes_by_normalized_url() -> None:
    html = """
    <a href="/subsidies/zuid/">Zuid</a>
    <a href="https://www.amsterdam.nl/subsidies/zuid">Amsterdam Zuid</a>
    """
    pages = parse_district_pages(html, page_url=ENTRY)
    assert len(pages) == 1
    assert pages[0].slug == "zuid"


def test_parse_district_pages_label_fallback_for_empty_anchor() -> None:
    html = '<a href="/subsidies/nieuwwest/"></a>'
    pages = parse_district_pages(html, page_url=ENTRY)
    assert pages[0].label == "Nieuw-West"


@pytest.mark.parametrize(
    "href",
    [
        "/subsidies/subsidies-onderwerp/",
        "https://example.com/subsidies/centrum/",
    ],
)
def test_parse_district_pages_skips_non_district_links(href: str) -> None:
    html = f'<a href="{href}">Skip</a>'
    assert parse_district_pages(html, page_url=ENTRY) == []


def test_parse_entry_fixture_finds_eight_stadsdeel_links() -> None:
    html = (FIXTURE_DIR / "entry-subsidies-onderwerp.html").read_text(encoding="utf-8")
    pages = parse_district_pages(html, page_url=ENTRY)
    assert [page.slug for page in pages] == [
        "centrum",
        "nieuwwest",
        "noord",
        "oost",
        "weesp",
        "west",
        "zuid",
        "zuidoost",
    ]
    assert pages[0] == DistrictPage(
        slug="centrum",
        label="Subsidies Centrum",
        url="https://www.amsterdam.nl/subsidies/centrum",
    )
    assert pages[4].url == (
        "https://www.amsterdam.nl/subsidies/subsidies-stadsgebied-weesp"
    )


def test_discover_district_pages_uses_mocked_entry_html(httpx_mock: object) -> None:
    html = (FIXTURE_DIR / "entry-subsidies-onderwerp.html").read_text(encoding="utf-8")
    httpx_mock.add_response(text=html)
    with create_client() as client:
        pages = discover_district_pages(ENTRY, client=client)
    assert len(pages) == 8
    assert pages[0].slug == "centrum"


def test_discover_district_pages_raises_on_blocked_response(
    httpx_mock: object,
) -> None:
    httpx_mock.add_response(
        status_code=403,
        text=f"<html><title>{ERROR_PAGE_TITLE_FRAGMENT}</title></html>",
    )
    with create_client() as client, pytest.raises(DiscoveryError, match="Blocked"):
        discover_district_pages(ENTRY, client=client)


@pytest.mark.network
def test_discover_district_pages_live_smoke() -> None:
    pages = discover_district_pages(ENTRY)
    assert len(pages) >= 7
