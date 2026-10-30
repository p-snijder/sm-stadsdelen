from pathlib import Path

from typer.testing import CliRunner

from stadsdelen.cli import app
from stadsdelen.discovery import WARMUP_URLS

runner = CliRunner()
ENTRY = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "html"
JSON_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
)

EMPTY_DISTRICT = '<div class="resultaten"></div>'


def _register_crawl_responses(httpx_mock: object) -> None:
    for _ in WARMUP_URLS:
        httpx_mock.add_response(text="<html></html>")
    entry_html = (FIXTURE_DIR / "entry-subsidies-onderwerp.html").read_text(
        encoding="utf-8"
    )
    httpx_mock.add_response(text=entry_html)
    district_html = {
        "centrum": (FIXTURE_DIR / "district-centrum.html").read_text(encoding="utf-8"),
        "nieuwwest": EMPTY_DISTRICT,
        "noord": (FIXTURE_DIR / "district-noord.html").read_text(encoding="utf-8"),
        "oost": EMPTY_DISTRICT,
        "weesp": EMPTY_DISTRICT,
        "west": EMPTY_DISTRICT,
        "zuid": EMPTY_DISTRICT,
        "zuidoost": EMPTY_DISTRICT,
    }
    for slug in (
        "centrum",
        "nieuwwest",
        "noord",
        "oost",
        "weesp",
        "west",
        "zuid",
        "zuidoost",
    ):
        httpx_mock.add_response(text=district_html[slug])


def test_enrich_e2e_mocked_http_writes_markdown_and_bak(
    tmp_path: Path,
    httpx_mock: object,
) -> None:
    target = tmp_path / "subsidies.json"
    target.write_text(JSON_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    original = target.read_bytes()
    bak_path = tmp_path / "subsidies.json.bak"

    _register_crawl_responses(httpx_mock)
    result = runner.invoke(
        app,
        ["enrich", "--entry-url", ENTRY, str(target)],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert bak_path.exists()
    assert bak_path.read_bytes() == original
    text = target.read_text(encoding="utf-8")
    assert "Stadsdeel: Centrum, Noord." in text
    assert "Stadsdeel: Centrum." in text
    assert "unknown-regeling" in text
    assert "Wrote updated JSON in place." in result.stderr + result.stdout

    after_first = target.read_bytes()
    _register_crawl_responses(httpx_mock)
    second = runner.invoke(
        app,
        ["enrich", "--entry-url", ENTRY, "--no-backup", str(target)],
    )
    assert second.exit_code == 0
    assert target.read_bytes() == after_first
    assert "No markdown changes; file not written." in second.stderr + second.stdout


def test_crawl_map_out_then_enrich_map_in_matches_live_enrich(
    tmp_path: Path,
    httpx_mock: object,
) -> None:
    map_path = tmp_path / "index.json"
    target_a = tmp_path / "a.json"
    target_b = tmp_path / "b.json"
    payload = JSON_FIXTURE.read_text(encoding="utf-8")
    target_a.write_text(payload, encoding="utf-8")
    target_b.write_text(payload, encoding="utf-8")

    _register_crawl_responses(httpx_mock)
    crawl = runner.invoke(
        app,
        ["crawl", "--map-out", str(map_path), "--entry-url", ENTRY],
    )
    assert crawl.exit_code == 0, crawl.stdout + crawl.stderr
    assert map_path.exists()

    _register_crawl_responses(httpx_mock)
    live = runner.invoke(
        app,
        ["enrich", "--no-backup", "--entry-url", ENTRY, str(target_a)],
    )
    assert live.exit_code == 0, live.stdout + live.stderr

    cached = runner.invoke(
        app,
        ["enrich", "--no-backup", "--map-in", str(map_path), str(target_b)],
    )
    assert cached.exit_code == 0, cached.stdout + cached.stderr
    assert target_a.read_text(encoding="utf-8") == target_b.read_text(encoding="utf-8")
