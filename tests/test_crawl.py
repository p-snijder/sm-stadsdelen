from stadsdelen.crawl import is_subsidy_detail_url, parse_subsidy_links

DISTRICT_PAGE = "https://www.amsterdam.nl/subsidies/centrum/"


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
