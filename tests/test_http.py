from unittest.mock import patch

import httpx
import pytest

from stadsdelen.http import (
    BROWSER_FETCH_INSTALL_HINT,
    ERROR_PAGE_TITLE_FRAGMENT,
    BrowserFetchError,
    FetchSession,
    _curl_response_to_httpx,
    create_client,
    fetch_text,
    is_blocked_or_error_page,
    resolve_browser_fetch,
)


def test_is_blocked_or_error_page_on_403() -> None:
    response = httpx.Response(403, text="<html><title>Forbidden</title></html>")
    assert is_blocked_or_error_page(response, response.text)


def test_is_blocked_or_error_page_on_amsterdam_error_title() -> None:
    html = f"<html><head><title>{ERROR_PAGE_TITLE_FRAGMENT}</title></head></html>"
    response = httpx.Response(200, text=html)
    assert is_blocked_or_error_page(response, html)


def test_is_blocked_or_error_page_on_ok_page() -> None:
    html = "<html><head><title>Subsidies</title></head><body>OK</body></html>"
    response = httpx.Response(200, text=html)
    assert not is_blocked_or_error_page(response, html)


def test_resolve_browser_fetch_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STADSDELEN_BROWSER_FETCH", raising=False)
    assert not resolve_browser_fetch()
    monkeypatch.setenv("STADSDELEN_BROWSER_FETCH", "1")
    assert resolve_browser_fetch()
    assert not resolve_browser_fetch(cli_flag=False)


def test_curl_response_to_httpx_maps_url() -> None:
    class FakeCurlResponse:
        status_code = 200
        text = "<html>ok</html>"
        url = "https://www.amsterdam.nl/final/"

    wrapped = _curl_response_to_httpx(
        FakeCurlResponse(),
        request_url="https://www.amsterdam.nl/start/",
    )
    assert wrapped.status_code == 200
    assert str(wrapped.url) == "https://www.amsterdam.nl/final/"


def test_fetch_session_auto_retries_with_browser_on_block(
    httpx_mock: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    httpx_mock.add_response(status_code=403, text="blocked")
    ok = httpx.Response(
        200,
        text="<html>ok</html>",
        request=httpx.Request("GET", "https://www.amsterdam.nl/ok/"),
    )

    def fake_curl_get(self: FetchSession, url: str) -> httpx.Response:
        assert url == "https://www.amsterdam.nl/subsidies/"
        return ok

    monkeypatch.setattr("stadsdelen.http._curl_cffi_available", lambda: True)

    def noop_require() -> object:
        return object()

    monkeypatch.setattr("stadsdelen.http._require_curl_cffi", noop_require)

    def fake_ensure(self: FetchSession) -> None:
        self._curl_session = object()

    monkeypatch.setattr(FetchSession, "_ensure_curl_session", fake_ensure)
    monkeypatch.setattr(FetchSession, "_curl_get", fake_curl_get)

    with create_client() as client:
        response = client.get("https://www.amsterdam.nl/subsidies/")
    assert response.status_code == 200
    assert response.text == "<html>ok</html>"


def test_create_client_browser_fetch_requires_curl_cffi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("stadsdelen.http._curl_cffi_available", lambda: False)

    def fail_import() -> None:
        raise BrowserFetchError(BROWSER_FETCH_INSTALL_HINT)

    monkeypatch.setattr("stadsdelen.http._require_curl_cffi", fail_import)
    with pytest.raises(BrowserFetchError, match="uv sync --extra browser"):
        create_client(browser_fetch=True)


def test_fetch_text_success(httpx_mock: object) -> None:
    httpx_mock.add_response(text="<html>ok</html>")
    with create_client() as client:
        response, text = fetch_text("https://www.amsterdam.nl/", client=client)
    assert response.status_code == 200
    assert text == "<html>ok</html>"


def test_create_client_request_delay_runs_after_get(httpx_mock: object) -> None:
    httpx_mock.add_response(text="ok")
    with patch("stadsdelen.http.time.sleep") as sleep_mock:
        with create_client(request_delay_seconds=0.5) as client:
            client.get("https://www.amsterdam.nl/")
    sleep_mock.assert_called_once_with(0.5)
