import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from stadsdelen.cli import app
from stadsdelen.crawl import CrawlReport
from stadsdelen.discovery import DistrictPage
from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.map_cache import load_index_cache

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
)
INDEX_FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidy-index-v1.json"
)


def _mock_crawl(sample_match_index: UrlToDistrictsIndex) -> tuple[object, object]:
    districts = [
        DistrictPage(
            slug="centrum",
            label="Subsidies Centrum",
            url="https://www.amsterdam.nl/subsidies/centrum",
        ),
    ]
    report = CrawlReport(
        by_district=(),
        index_size=len(sample_match_index),
        http_failures=(),
    )
    return districts, (sample_match_index, report)


def test_enrich_invalid_json_exits_one(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    index: UrlToDistrictsIndex = {}
    districts, build_return = _mock_crawl(index)
    with (
        patch("stadsdelen.cli.warm_session"),
        patch("stadsdelen.cli.discover_district_pages", return_value=districts),
        patch("stadsdelen.cli.build_subsidy_index", return_value=build_return),
    ):
        result = runner.invoke(app, ["enrich", str(bad)])
    assert result.exit_code == 1
    combined = result.stdout + result.stderr
    assert "Invalid JSON" in combined


def test_enrich_dry_run_does_not_write_file(
    tmp_path: Path,
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    target = tmp_path / "subsidies.json"
    shutil.copy(FIXTURE, target)
    before = target.read_bytes()
    districts, build_return = _mock_crawl(sample_match_index)
    with (
        patch("stadsdelen.cli.warm_session"),
        patch("stadsdelen.cli.discover_district_pages", return_value=districts),
        patch("stadsdelen.cli.build_subsidy_index", return_value=build_return),
    ):
        result = runner.invoke(app, ["enrich", "--dry-run", str(target)])
    assert result.exit_code == 0
    assert target.read_bytes() == before
    combined = result.stdout + result.stderr
    assert "Dry run: no file written." in combined
    assert "Markdown updated: 2" in combined


def test_enrich_skips_write_when_no_markdown_changes(
    tmp_path: Path,
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    target = tmp_path / "subsidies.json"
    shutil.copy(FIXTURE, target)
    districts, build_return = _mock_crawl(sample_match_index)
    with (
        patch("stadsdelen.cli.warm_session"),
        patch("stadsdelen.cli.discover_district_pages", return_value=districts),
        patch("stadsdelen.cli.build_subsidy_index", return_value=build_return),
    ):
        first = runner.invoke(app, ["enrich", "--no-backup", str(target)])
        assert first.exit_code == 0
        after_first = target.read_bytes()
        second = runner.invoke(app, ["enrich", "--no-backup", str(target)])
    assert second.exit_code == 0
    assert target.read_bytes() == after_first
    combined = second.stdout + second.stderr
    assert "No markdown changes; file not written." in combined
    assert "Markdown skipped (already correct): 2" in combined


def test_crawl_writes_map_out_with_mocked_http(
    tmp_path: Path,
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    map_path = tmp_path / "index.json"
    districts = [
        DistrictPage(
            slug="centrum",
            label="Subsidies Centrum",
            url="https://www.amsterdam.nl/subsidies/centrum",
        ),
    ]
    report = CrawlReport(
        by_district=(),
        index_size=len(sample_match_index),
        http_failures=(),
    )
    with (
        patch("stadsdelen.cli.warm_session"),
        patch("stadsdelen.cli.discover_district_pages", return_value=districts),
        patch(
            "stadsdelen.cli.build_subsidy_index",
            return_value=(sample_match_index, report),
        ),
    ):
        result = runner.invoke(
            app,
            ["crawl", "--map-out", str(map_path)],
        )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert map_path.exists()
    assert load_index_cache(map_path) == sample_match_index
    assert "Subsidy URLs indexed: 2" in result.stderr + result.stdout


def test_crawl_browser_fetch_enables_create_client_flag(
    tmp_path: Path,
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    map_path = tmp_path / "index.json"
    districts = [
        DistrictPage(
            slug="centrum",
            label="Subsidies Centrum",
            url="https://www.amsterdam.nl/subsidies/centrum",
        ),
    ]
    report = CrawlReport(
        by_district=(),
        index_size=len(sample_match_index),
        http_failures=(),
    )
    fake_client = MagicMock()
    with (
        patch("stadsdelen.cli.create_client", return_value=fake_client) as mock_create,
        patch("stadsdelen.cli.warm_session"),
        patch("stadsdelen.cli.discover_district_pages", return_value=districts),
        patch(
            "stadsdelen.cli.build_subsidy_index",
            return_value=(sample_match_index, report),
        ),
    ):
        result = runner.invoke(
            app,
            ["crawl", "--browser-fetch", "--map-out", str(map_path)],
        )
    assert result.exit_code == 0, result.stdout + result.stderr
    mock_create.assert_called_once_with(
        timeout=30.0,
        request_delay_seconds=0.0,
        browser_fetch=True,
    )
    fake_client.close.assert_called_once()


def test_enrich_map_in_skips_live_crawl(
    tmp_path: Path,
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    target = tmp_path / "subsidies.json"
    shutil.copy(FIXTURE, target)
    with (
        patch("stadsdelen.cli.warm_session") as warm,
        patch("stadsdelen.cli.discover_district_pages") as discover,
        patch("stadsdelen.cli.build_subsidy_index") as build,
    ):
        result = runner.invoke(
            app,
            [
                "enrich",
                "--dry-run",
                "--map-in",
                str(INDEX_FIXTURE),
                str(target),
            ],
        )
    warm.assert_not_called()
    discover.assert_not_called()
    build.assert_not_called()
    assert result.exit_code == 0
    assert "Markdown updated: 2" in result.stdout + result.stderr


def test_enrich_strict_exits_on_unmatched_rows(
    tmp_path: Path,
) -> None:
    target = tmp_path / "subsidies.json"
    shutil.copy(FIXTURE, target)
    result = runner.invoke(
        app,
        [
            "enrich",
            "--strict",
            "--dry-run",
            "--map-in",
            str(INDEX_FIXTURE),
            str(target),
        ],
    )
    assert result.exit_code == 1
    assert "Unmatched: 2" in result.stdout + result.stderr


def test_enrich_dry_run_skips_map_out(
    tmp_path: Path,
    sample_match_index: UrlToDistrictsIndex,
) -> None:
    target = tmp_path / "subsidies.json"
    map_path = tmp_path / "out.json"
    shutil.copy(FIXTURE, target)
    report = CrawlReport(by_district=(), index_size=2, http_failures=())
    with (
        patch("stadsdelen.cli.warm_session"),
        patch("stadsdelen.cli.discover_district_pages"),
        patch(
            "stadsdelen.cli.build_subsidy_index",
            return_value=(sample_match_index, report),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "enrich",
                "--dry-run",
                "--map-out",
                str(map_path),
                str(target),
            ],
        )
    assert result.exit_code == 0
    assert not map_path.exists()
