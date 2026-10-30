"""HTTP helpers for fetching Amsterdam subsidy pages.

amsterdam.nl often returns HTTP 403 or a generic error page
(``Er is iets mis gegaan``) to simple clients. Callers should use
``is_blocked_or_error_page`` before parsing HTML.
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Any, Protocol

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterable

log = logging.getLogger(__name__)

ERROR_PAGE_TITLE_FRAGMENT = "Er is iets mis gegaan"

BROWSER_FETCH_ENV_VAR = "STADSDELEN_BROWSER_FETCH"
DEFAULT_IMPERSONATE = "chrome120"
BROWSER_FETCH_INSTALL_HINT = (
    "Install browser fetch support with `uv sync --extra browser`, "
    "then pass `--browser-fetch` or set STADSDELEN_BROWSER_FETCH=1."
)

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


class BrowserFetchError(ImportError):
    """Raised when browser fetch was requested but curl-cffi is not installed."""


class HttpSession(Protocol):
    """Minimal client surface used by discovery and crawl."""

    def get(self, url: str) -> httpx.Response: ...

    def close(self) -> None: ...


def resolve_browser_fetch(*, cli_flag: bool | None = None) -> bool:
    """Resolve browser fetch from CLI flag or ``STADSDELEN_BROWSER_FETCH``."""
    if cli_flag is not None:
        return cli_flag
    return os.environ.get(BROWSER_FETCH_ENV_VAR, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def blocked_fetch_hint() -> str:
    """Short hint appended when amsterdam.nl blocks a plain HTTP client."""
    if _curl_cffi_available():
        return (
            " Retry with `--browser-fetch` or set STADSDELEN_BROWSER_FETCH=1."
        )
    return f" {BROWSER_FETCH_INSTALL_HINT}"


def _curl_cffi_available() -> bool:
    try:
        import curl_cffi  # noqa: F401

        return True
    except ImportError:
        return False


def _require_curl_cffi() -> Any:
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as exc:
        raise BrowserFetchError(BROWSER_FETCH_INSTALL_HINT) from exc
    return curl_requests


def _curl_response_to_httpx(response: Any, *, request_url: str) -> httpx.Response:
    final_url = str(getattr(response, "url", request_url))
    request = httpx.Request("GET", final_url)
    return httpx.Response(
        response.status_code,
        text=response.text,
        request=request,
    )


def _build_httpx_client(
    *,
    request_delay_seconds: float,
    kwargs: dict[str, object],
) -> httpx.Client:
    headers = dict(DEFAULT_HEADERS)
    extra = kwargs.pop("headers", None)
    if extra:
        headers.update(extra)

    event_hooks: dict[str, list] = dict(kwargs.pop("event_hooks", {}) or {})
    if request_delay_seconds > 0:
        delay = request_delay_seconds

        def _pace_response(response: httpx.Response) -> None:
            time.sleep(delay)

        response_hooks = list(event_hooks.get("response", []))
        response_hooks.append(_pace_response)
        event_hooks["response"] = response_hooks

    client_kwargs: dict[str, object] = {
        "headers": headers,
        "follow_redirects": True,
        **kwargs,
    }
    if event_hooks:
        client_kwargs["event_hooks"] = event_hooks
    return httpx.Client(**client_kwargs)


class FetchSession:
    """HTTP session with optional curl-cffi impersonation and auto-retry."""

    def __init__(
        self,
        *,
        browser_fetch: bool = False,
        auto_retry_on_block: bool = True,
        request_delay_seconds: float = 0.0,
        impersonate: str = DEFAULT_IMPERSONATE,
        **kwargs: object,
    ) -> None:
        self._request_delay = request_delay_seconds
        self._impersonate = impersonate
        self._timeout = float(kwargs.pop("timeout", 30.0))
        self._using_browser = browser_fetch
        self._auto_retry = auto_retry_on_block and not browser_fetch
        self._curl_session: Any | None = None
        self._httpx: httpx.Client | None = None
        if browser_fetch:
            _require_curl_cffi()
            self._ensure_curl_session()
        else:
            self._httpx = _build_httpx_client(
                request_delay_seconds=request_delay_seconds,
                kwargs=kwargs,
            )

    def _ensure_curl_session(self) -> None:
        if self._curl_session is not None:
            return
        curl_requests = _require_curl_cffi()
        self._curl_session = curl_requests.Session(impersonate=self._impersonate)

    def _pace(self) -> None:
        if self._request_delay > 0:
            time.sleep(self._request_delay)

    def _curl_get(self, url: str) -> httpx.Response:
        self._ensure_curl_session()
        assert self._curl_session is not None
        response = self._curl_session.get(url, timeout=self._timeout)
        self._pace()
        return _curl_response_to_httpx(response, request_url=url)

    def _upgrade_to_browser(self) -> None:
        if self._using_browser:
            return
        log.info(
            "amsterdam.nl blocked plain HTTP client; retrying with browser fetch "
            "(%s) for remaining requests",
            self._impersonate,
        )
        self._using_browser = True
        self._auto_retry = False
        if self._httpx is not None:
            self._httpx.close()
            self._httpx = None
        _require_curl_cffi()
        self._ensure_curl_session()

    def get(self, url: str) -> httpx.Response:
        if self._using_browser:
            return self._curl_get(url)

        assert self._httpx is not None
        response = self._httpx.get(url)
        if self._auto_retry and is_blocked_or_error_page(response, response.text):
            if _curl_cffi_available():
                self._upgrade_to_browser()
                return self._curl_get(url)
        return response

    def close(self) -> None:
        if self._httpx is not None:
            self._httpx.close()
            self._httpx = None
        if self._curl_session is not None:
            close = getattr(self._curl_session, "close", None)
            if callable(close):
                close()
            self._curl_session = None

    def __enter__(self) -> FetchSession:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def create_client(
    *,
    request_delay_seconds: float = 0.0,
    browser_fetch: bool = False,
    auto_retry_on_block: bool = True,
    **kwargs: object,
) -> HttpSession:
    """Return a sync client with default browser-like headers."""
    if browser_fetch or auto_retry_on_block:
        return FetchSession(
            browser_fetch=browser_fetch,
            auto_retry_on_block=auto_retry_on_block,
            request_delay_seconds=request_delay_seconds,
            **kwargs,
        )
    return _build_httpx_client(
        request_delay_seconds=request_delay_seconds,
        kwargs=dict(kwargs),
    )


def fetch_text(
    url: str,
    *,
    client: HttpSession | None = None,
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


def warm_session(client: HttpSession, urls: Iterable[str]) -> None:
    """Visit URLs in order to accumulate cookies before the target page."""
    for url in urls:
        client.get(url)
