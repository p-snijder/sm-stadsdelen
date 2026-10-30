"""HTTP helpers for fetching Amsterdam subsidy pages.

amsterdam.nl often returns HTTP 403 or a generic error page
(``Er is iets mis gegaan``) to simple clients. Callers should use
``is_blocked_or_error_page`` before parsing HTML.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterable

ERROR_PAGE_TITLE_FRAGMENT = "Er is iets mis gegaan"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

RETRYABLE_STATUS_CODES = frozenset({429, 503})


def create_client(**kwargs: object) -> httpx.Client:
    """Return a sync client with default browser-like headers."""
    headers = dict(DEFAULT_HEADERS)
    extra = kwargs.pop("headers", None)
    if extra:
        headers.update(extra)
    return httpx.Client(headers=headers, follow_redirects=True, **kwargs)


def fetch_text(
    url: str,
    *,
    client: httpx.Client | None = None,
    max_retries: int = 3,
    retry_backoff_seconds: float = 1.0,
) -> tuple[httpx.Response, str]:
    """GET ``url`` and return the response plus decoded response text."""
    own_client = client is None
    http = client if client is not None else create_client()
    try:
        last_response: httpx.Response | None = None
        for attempt in range(max_retries):
            response = http.get(url)
            last_response = response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                break
            if attempt < max_retries - 1:
                time.sleep(retry_backoff_seconds * (attempt + 1))
        assert last_response is not None
        last_response.raise_for_status()
        return last_response, last_response.text
    finally:
        if own_client:
            http.close()


def is_blocked_or_error_page(response: httpx.Response, text: str) -> bool:
    """True when the response looks like a block or Amsterdam error page."""
    if response.status_code >= 400:
        return True
    lowered = text.lower()
    if ERROR_PAGE_TITLE_FRAGMENT.lower() in lowered:
        return True
    if "<title>" in lowered and "mis gegaan" in lowered:
        return True
    return False


def warm_session(client: httpx.Client, urls: Iterable[str]) -> None:
    """Visit URLs in order to accumulate cookies before the target page."""
    for url in urls:
        client.get(url)
