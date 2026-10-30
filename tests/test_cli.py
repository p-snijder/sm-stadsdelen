import shutil
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from stadsdelen.cli import app
from stadsdelen.crawl import CrawlReport
from stadsdelen.discovery import DistrictPage
from stadsdelen.index import UrlToDistrictsIndex

runner = CliRunner()
FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "json" / "subsidies-sample.json"
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
