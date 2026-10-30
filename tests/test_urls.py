import pytest

from stadsdelen.urls import normalize, resolve

ENTRY = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "https://www.amsterdam.nl/subsidies/foo/",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "http://www.amsterdam.nl/subsidies/foo",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "https://amsterdam.nl/subsidies/foo",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "https://www.amsterdam.nl/subsidies/foo#section",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "https://www.amsterdam.nl/subsidies/foo?utm_source=test",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "https://www.amsterdam.nl//subsidies//foo//",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "https://www.amsterdam.nl/Subsidies/Foo/",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
        (
            "https://www.amsterdam.nl/",
            "https://www.amsterdam.nl/",
        ),
        (
            "//www.amsterdam.nl/subsidies/foo/",
            "https://www.amsterdam.nl/subsidies/foo",
        ),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_resolve_relative_href() -> None:
    assert resolve("/subsidies/example/", ENTRY) == (
        "https://www.amsterdam.nl/subsidies/example"
    )


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "   ",
        "/subsidies/only-path",
        "ftp://www.amsterdam.nl/subsidies/foo",
    ],
)
def test_normalize_rejects_invalid(invalid: str) -> None:
    with pytest.raises(ValueError):
        normalize(invalid)
