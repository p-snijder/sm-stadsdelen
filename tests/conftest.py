import pytest

from stadsdelen.index import UrlToDistrictsIndex

ENTRY = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"


@pytest.fixture
def sample_match_index() -> UrlToDistrictsIndex:
    """Minimal index aligned with tests/fixtures/json/subsidies-sample.json."""
    shared = "https://www.amsterdam.nl/subsidies/city-wide-regeling"
    centrum_only = "https://www.amsterdam.nl/subsidies/bewonersinitiatieven-centrum"
    return {
        shared: ["Subsidies Centrum", "Subsidies Noord"],
        centrum_only: ["Subsidies Centrum"],
    }
