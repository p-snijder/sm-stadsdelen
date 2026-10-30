"""Typer CLI for stadsdeel subsidy enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
import typer

from stadsdelen.crawl import CrawlError, build_subsidy_index
from stadsdelen.discovery import (
    DEFAULT_ENTRY_URL,
    WARMUP_URLS,
    DiscoveryError,
    discover_district_pages,
)
from stadsdelen.http import create_client, warm_session
from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.json_io import (
    JsonLoadError,
    JsonSaveError,
    load_subsidy_array,
    save_subsidy_array,
)
from stadsdelen.markdown import enrich_subsidies
from stadsdelen.reporting import format_enrich_run_summary

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Crawl Amsterdam stadsdeel subsidy pages and enrich JSON records.",
)

enrich_app = typer.Typer(
    help="Crawl stadsdeel pages, match URLs, prepend Stadsdeel markdown, save in place.",
)
app.add_typer(enrich_app, name="enrich")


@dataclass(frozen=True)
class EnrichRunResult:
    """Outcome of a full enrich pipeline run."""

    summary: str
    wrote_file: bool


def run_enrich(
    json_path: Path,
    *,
    entry_url: str = DEFAULT_ENTRY_URL,
    dry_run: bool = False,
    backup: bool = True,
    index: UrlToDistrictsIndex | None = None,
    client: httpx.Client | None = None,
) -> EnrichRunResult:
    """Crawl (unless index given), match, enrich, and optionally save JSON in place."""
    own_client = client is None
    http = client if client is not None else create_client(timeout=30.0)
    crawl_report = None

    try:
        if index is None:
            if own_client:
                warm_session(http, WARMUP_URLS)
            districts = discover_district_pages(entry_url, client=http)
            index, crawl_report = build_subsidy_index(districts, client=http)

        records = load_subsidy_array(json_path)
        match_result, enrich_result = enrich_subsidies(records, index)

        wrote_file = False
        if not dry_run and enrich_result.updated > 0:
            save_subsidy_array(json_path, records, backup=backup)
            wrote_file = True

        summary = format_enrich_run_summary(
            crawl=crawl_report,
            match=match_result,
            enrich=enrich_result,
            dry_run=dry_run,
            wrote_file=wrote_file,
        )
        return EnrichRunResult(summary=summary, wrote_file=wrote_file)
    finally:
        if own_client:
            http.close()


@enrich_app.callback(invoke_without_command=True)
def enrich_cmd(
    ctx: typer.Context,
    json_path: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to subsidy JSON array file (updated in place).",
    ),
    entry_url: str = typer.Option(
        DEFAULT_ENTRY_URL,
        "--entry-url",
        help="Amsterdam subsidies overview URL for stadsdeel discovery.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Crawl and enrich in memory; do not write the JSON file.",
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Skip copying input to .bak before overwrite.",
    ),
) -> None:
    """Run the enrich pipeline when ``stadsdelen enrich PATH`` is invoked."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        result = run_enrich(
            json_path,
            entry_url=entry_url,
            dry_run=dry_run,
            backup=not no_backup,
        )
    except (CrawlError, DiscoveryError, JsonLoadError, JsonSaveError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result.summary, err=True)
