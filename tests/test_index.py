from stadsdelen.index import IndexBuilder, UrlToDistrictsIndex


def test_index_builder_merges_same_url_across_districts() -> None:
    builder = IndexBuilder()
    url = "https://www.amsterdam.nl/subsidies/shared-regeling"
    builder.add_district_urls([url], "Centrum")
    builder.add_district_urls([url], "Noord")
    index = builder.finalize()
    assert index[url] == ["Centrum", "Noord"]


def test_index_builder_dedupes_duplicate_label() -> None:
    builder = IndexBuilder()
    url = "https://www.amsterdam.nl/subsidies/foo"
    builder.add_district_urls([url, url], "Zuid")
    assert builder.finalize()[url] == ["Zuid"]


def test_index_builder_sorts_labels_stably() -> None:
    builder = IndexBuilder()
    url = "https://www.amsterdam.nl/subsidies/bar"
    builder.add_district_urls([url], "Zuidoost")
    builder.add_district_urls([url], "Centrum")
    builder.add_district_urls([url], "Noord")
    assert builder.finalize()[url] == ["Centrum", "Noord", "Zuidoost"]


def test_index_builder_empty() -> None:
    assert IndexBuilder().finalize() == {}


def test_index_builder_ignores_empty_label() -> None:
    builder = IndexBuilder()
    builder.add_district_urls(["https://www.amsterdam.nl/subsidies/x"], "  ")
    assert builder.finalize() == {}


def test_finalize_returns_sorted_url_keys() -> None:
    builder = IndexBuilder()
    builder.add_district_urls(["https://www.amsterdam.nl/subsidies/z"], "A")
    builder.add_district_urls(["https://www.amsterdam.nl/subsidies/a"], "B")
    index: UrlToDistrictsIndex = builder.finalize()
    assert list(index.keys()) == [
        "https://www.amsterdam.nl/subsidies/a",
        "https://www.amsterdam.nl/subsidies/z",
    ]
