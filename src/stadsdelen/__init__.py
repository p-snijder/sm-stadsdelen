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
from stadsdelen.json_io import JsonLoadError, load_subsidy_array
from stadsdelen.markdown import (
    MarkdownUpdateStatus,
    enrich_matched_rows,
    enrich_subsidies,
    update_markdown,
)
from stadsdelen.match import match_subsidies, match_subsidies_file
from stadsdelen.reporting import (
    EnrichResult,
    MatchedRow,
    MatchResult,
    UnmatchedRow,
    format_enrich_report,
    format_match_report,
)
from stadsdelen.urls import normalize, resolve

__all__ = [
    "CrawlError",
    "CrawlReport",
    "DiscoveryError",
    "DistrictPage",
    "EnrichResult",
    "JsonLoadError",
    "MarkdownUpdateStatus",
    "MatchedRow",
    "MatchResult",
    "UnmatchedRow",
    "UrlToDistrictsIndex",
    "__version__",
    "build_subsidy_index",
    "discover_district_pages",
    "enrich_matched_rows",
    "enrich_subsidies",
    "format_enrich_report",
    "format_match_report",
    "is_district_overview_url",
    "load_subsidy_array",
    "match_subsidies",
    "match_subsidies_file",
    "normalize",
    "parse_district_pages",
    "resolve",
    "update_markdown",
]
