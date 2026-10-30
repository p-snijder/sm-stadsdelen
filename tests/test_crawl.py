from pathlib import Path

from stadsdelen.crawl import (
    crawl_district_subsidy_urls,
    is_subsidy_detail_url,
    parse_pagination_next_url,
    parse_subsidy_links,
)
from stadsdelen.discovery import DistrictPage
from stadsdelen.http import create_client

DISTRICT_PAGE = "https://www.amsterdam.nl/subsidies/centrum/"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "html"


def test_is_subsidy_detail_url_accepts_regulation_paths() -> None:
    assert is_subsidy_detail_url(
        "https://www.amsterdam.nl/subsidies/bewonersinitiatieven-centrum"
    )
    assert is_subsidy_detail_url(
        "https://www.amsterdam.nl/subsidies/centrum/aanpak-binnenstad"
    )


def test_is_subsidy_detail_url_rejects_overview_and_nav() -> None:
    assert not is_subsidy_detail_url("https://www.amsterdam.nl/subsidies/centrum")
    assert not is_subsidy_detail_url(
        "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/subsidies-duurzaam"
    )
    assert not is_subsidy_detail_url("https://www.amsterdam.nl/subsidies/niet-meer")
    assert not is_subsidy_detail_url("https://example.com/subsidies/foo")


def test_parse_subsidy_links_from_resultaat_blocks() -> None:
    html = """
    <div class="resultaten">
      <div class="resultaat">
        <h2 class="link"><a href="/subsidies/regeling-a/">Regeling A</a></h2>
      </div>
      <div class="resultaat">
        <h2 class="link"><a href="https://www.amsterdam.nl/subsidies/regeling-b">B</a></h2>
      </div>
    </div>
    """
    links = parse_subsidy_links(html, page_url=DISTRICT_PAGE)
    assert links == [
        "https://www.amsterdam.nl/subsidies/regeling-a",
        "https://www.amsterdam.nl/subsidies/regeling-b",
    ]


def test_parse_subsidy_links_skips_district_and_topic_links() -> None:
    html = """
    <div class="resultaten">
      <div class="resultaat">
        <h2 class="link"><a href="/subsidies/noord/">Noord</a></h2>
      </div>
      <div class="resultaat">
        <h2 class="link"><a href="/subsidies/subsidies-onderwerp/x/">Topic</a></h2>
      </div>
      <div class="resultaat">
        <h2 class="link"><a href="/subsidies/good-one/">Good</a></h2>
      </div>
    </div>
    """
    assert parse_subsidy_links(html, page_url=DISTRICT_PAGE) == [
        "https://www.amsterdam.nl/subsidies/good-one",
    ]


def test_parse_subsidy_links_dedupes_normalized_urls() -> None:
    html = """
    <div class="resultaten">
      <div class="resultaat">
        <h2 class="link"><a href="/subsidies/foo/">One</a></h2>
      </div>
      <div class="resultaat">
        <h2 class="link"><a href="https://www.amsterdam.nl/subsidies/foo">One again</a></h2>
      </div>
    </div>
    """
    assert len(parse_subsidy_links(html, page_url=DISTRICT_PAGE)) == 1


def test_parse_district_centrum_fixture() -> None:
    html = (FIXTURE_DIR / "district-centrum.html").read_text(encoding="utf-8")
    links = parse_subsidy_links(html, page_url=DISTRICT_PAGE)
    assert links == [
        "https://www.amsterdam.nl/subsidies/aanpak-binnenstad",
        "https://www.amsterdam.nl/subsidies/bewonersinitiatieven-centrum",
        "https://www.amsterdam.nl/subsidies/city-wide-regeling",
    ]


def test_parse_district_noord_fixture() -> None:
    html = (FIXTURE_DIR / "district-noord.html").read_text(encoding="utf-8")
    page = "https://www.amsterdam.nl/subsidies/noord/"
    links = parse_subsidy_links(html, page_url=page)
    assert links == [
        "https://www.amsterdam.nl/subsidies/buurtbudgetten-noord",
        "https://www.amsterdam.nl/subsidies/city-wide-regeling",
    ]


def test_parse_pagination_next_url_resolves_relative_href() -> None:
    html = """
    <div class="resultaten">
      <a class="startagain" href="/subsidies/zuid/pagina-2/">Volgende</a>
    </div>
    """
    assert parse_pagination_next_url(
        html, page_url="https://www.amsterdam.nl/subsidies/zuid/"
    ) == "https://www.amsterdam.nl/subsidies/zuid/pagina-2"


def test_parse_pagination_next_url_returns_none_when_missing() -> None:
    assert parse_pagination_next_url("<html></html>", page_url=DISTRICT_PAGE) is None


def test_crawl_district_subsidy_urls_follows_pagination(httpx_mock: object) -> None:
    page1 = """
    <div class="resultaten">
      <div class="resultaat"><h2 class="link"><a href="/subsidies/page-one/">One</a></h2></div>
      <a class="startagain" href="/subsidies/zuid/pagina-2/">Volgende</a>
    </div>
    """
    page2 = """
    <div class="resultaten">
      <div class="resultaat"><h2 class="link"><a href="/subsidies/page-two/">Two</a></h2></div>
    </div>
    """
    district = DistrictPage(
        slug="zuid",
        label="Zuid",
        url="https://www.amsterdam.nl/subsidies/zuid",
    )
    httpx_mock.add_response(text=page1)
    httpx_mock.add_response(text=page2)
    with create_client() as client:
        urls, stats = crawl_district_subsidy_urls(district, client=client)
    assert urls == [
        "https://www.amsterdam.nl/subsidies/page-one",
        "https://www.amsterdam.nl/subsidies/page-two",
    ]
    assert stats.pages_fetched == 2
    assert stats.subsidy_links_unique == 2
    assert parse_pagination_next_url(page2, page_url=district.url) is None


def test_pagination_fixtures_page1_points_to_page2() -> None:
    page1 = (FIXTURE_DIR / "district-zuid-page1.html").read_text(encoding="utf-8")
    base = "https://www.amsterdam.nl/subsidies/zuid/"
    assert parse_pagination_next_url(page1, page_url=base) == (
        "https://www.amsterdam.nl/subsidies/zuid/pagina-2"
    )
    assert parse_subsidy_links(page1, page_url=base) == [
        "https://www.amsterdam.nl/subsidies/zuid-regeling-alpha",
    ]


def test_pagination_fixtures_collect_links_from_both_pages(httpx_mock: object) -> None:
    page1 = (FIXTURE_DIR / "district-zuid-page1.html").read_text(encoding="utf-8")
    page2 = (FIXTURE_DIR / "district-zuid-page2.html").read_text(encoding="utf-8")
    district = DistrictPage(
        slug="zuid",
        label="Zuid",
        url="https://www.amsterdam.nl/subsidies/zuid",
    )
    httpx_mock.add_response(text=page1)
    httpx_mock.add_response(text=page2)
    with create_client() as client:
        urls, stats = crawl_district_subsidy_urls(district, client=client)
    assert urls == [
        "https://www.amsterdam.nl/subsidies/zuid-regeling-alpha",
        "https://www.amsterdam.nl/subsidies/zuid-regeling-beta",
    ]
    assert stats.pages_fetched == 2
