import httpx

from stadsdelen.http import (
    ERROR_PAGE_TITLE_FRAGMENT,
    create_client,
    fetch_text,
    is_blocked_or_error_page,
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


def test_fetch_text_success(httpx_mock: object) -> None:
    httpx_mock.add_response(text="<html>ok</html>")
    with create_client() as client:
        response, text = fetch_text("https://www.amsterdam.nl/", client=client)
    assert response.status_code == 200
    assert text == "<html>ok</html>"
