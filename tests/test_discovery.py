import pytest

from stadsdelen.discovery import DistrictPage, parse_district_pages

ENTRY = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"


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
