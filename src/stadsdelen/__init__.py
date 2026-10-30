"""Amsterdam stadsdeel subsidy mapper."""

__version__ = "0.1.0"

from stadsdelen.crawl import (
    CrawlError,
    CrawlReport,
    build_subsidy_index,
)
from stadsdelen.discovery import (
    DiscoveryError,
    DistrictPage,
    discover_district_pages,
    is_district_overview_url,
    parse_district_pages,
)
from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.urls import normalize, resolve

__all__ = [
    "CrawlError",
    "CrawlReport",
    "DiscoveryError",
    "DistrictPage",
    "UrlToDistrictsIndex",
    "__version__",
    "build_subsidy_index",
    "discover_district_pages",
    "is_district_overview_url",
    "normalize",
    "parse_district_pages",
    "resolve",
]
