"""Amsterdam stadsdeel subsidy mapper."""

__version__ = "0.1.0"

from stadsdelen.discovery import (
    DiscoveryError,
    DistrictPage,
    discover_district_pages,
    parse_district_pages,
)
from stadsdelen.urls import normalize, resolve

__all__ = [
    "DiscoveryError",
    "DistrictPage",
    "__version__",
    "discover_district_pages",
    "normalize",
    "parse_district_pages",
    "resolve",
]
