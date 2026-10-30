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
from stadsdelen.http import create_client, resolve_browser_fetch, warm_session
from stadsdelen.index import UrlToDistrictsIndex
from stadsdelen.json_io import (
    JsonLoadError,
    JsonSaveError,
    load_subsidy_array,
    save_subsidy_array,
)
from stadsdelen.log_config import configure_logging, get_logger
from stadsdelen.map_cache import MapCacheError, load_index_cache, save_index_cache
from stadsdelen.markdown import enrich_subsidies
from stadsdelen.reporting import format_crawl_report, format_enrich_run_summary

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Crawl Amsterdam stadsdeel subsidy pages and enrich JSON records.",
)

enrich_app = typer.Typer(
    help=(
        "Crawl stadsdeel pages, match URLs, prepend Stadsdeel markdown, save in place."
    ),
)
app.add_typer(enrich_app, name="enrich")

crawl_app = typer.Typer(
    help="Discover stadsdeel pages, crawl subsidy links, write index cache.",
)
app.add_typer(crawl_app, name="crawl")


class StrictMatchError(Exception):
    """Raised when --strict is set and unmatched JSON rows remain."""


@dataclass(frozen=True)
class EnrichRunResult:
    """Outcome of a full enrich pipeline run."""

    summary: str
    wrote_file: bool
    strict_failed: bool = False


@dataclass(frozen=True)
class CrawlRunResult:
    """Outcome of a crawl-only run."""

    summary: str


def _resolve_log_level(verbose: bool, log_level: str | None) -> str:
    if log_level is not None:
        return log_level
    if verbose:
        return "INFO"
    return "WARNING"


@app.callback()
def main_callback(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Log INFO messages from the stadsdelen package.",
    ),
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        help="Log level for stadsdelen (warning, info, debug).",
    ),
) -> None:
    """Shared options for crawl and enrich subcommands."""
    configure_logging(_resolve_log_level(verbose, log_level))


def run_crawl(
    map_out: Path,
    *,
    entry_url: str = DEFAULT_ENTRY_URL,
    request_delay_seconds: float = 0.0,
    browser_fetch: bool | None = None,
    client: httpx.Client | None = None,
) -> CrawlRunResult:
    """Discover districts, crawl subsidy links, and write index cache."""
    log = get_logger("cli")
    own_client = client is None
    use_browser_fetch = resolve_browser_fetch(cli_flag=browser_fetch)
    http = (
        client
        if client is not None
        else create_client(
            timeout=30.0,
            request_delay_seconds=request_delay_seconds,
            browser_fetch=use_browser_fetch,
        )
    )

    try:
        if own_client:
            log.debug("Warming HTTP session")
            warm_session(http, WARMUP_URLS)
        log.info("Discovering district overview pages from %s", entry_url)
        districts = discover_district_pages(entry_url, client=http)
        log.info("Crawling %d district overview pages", len(districts))
        index, crawl_report = build_subsidy_index(districts, client=http)
        save_index_cache(map_out, index, entry_url=entry_url)
        log.info("Wrote index cache (%d URLs) to %s", len(index), map_out)
        summary = format_crawl_report(crawl_report)
        return CrawlRunResult(summary=summary)
    finally:
        if own_client:
            http.close()


def run_enrich(
    json_path: Path,
    *,
    entry_url: str = DEFAULT_ENTRY_URL,
    dry_run: bool = False,
    backup: bool = True,
    index: UrlToDistrictsIndex | None = None,
    map_in: Path | None = None,
    map_out: Path | None = None,
    strict: bool = False,
    request_delay_seconds: float = 0.0,
    browser_fetch: bool | None = None,
    client: httpx.Client | None = None,
) -> EnrichRunResult:
    """Crawl (unless index or map-in), match, enrich, and optionally save JSON."""
    log = get_logger("cli")
    crawl_report = None
    cache_entry_url: str | None = None
    needs_http = index is None and map_in is None
    own_client = needs_http and client is None
    use_browser_fetch = resolve_browser_fetch(cli_flag=browser_fetch)
    http = client
    if needs_http and http is None:
        http = create_client(
            timeout=30.0,
            request_delay_seconds=request_delay_seconds,
            browser_fetch=use_browser_fetch,
        )

    try:
        if index is None and map_in is not None:
            log.info("Loading index cache from %s", map_in)
            index = load_index_cache(map_in)
        elif index is None:
            assert http is not None
            if own_client:
                log.debug("Warming HTTP session")
                warm_session(http, WARMUP_URLS)
            log.info("Discovering district overview pages from %s", entry_url)
            districts = discover_district_pages(entry_url, client=http)
            log.info("Crawling %d district overview pages", len(districts))
            index, crawl_report = build_subsidy_index(districts, client=http)
            cache_entry_url = entry_url

        log.info("Matching and enriching JSON rows from %s", json_path)
        records = load_subsidy_array(json_path)
        match_result, enrich_result = enrich_subsidies(records, index)

        summary = format_enrich_run_summary(
            crawl=crawl_report,
            match=match_result,
            enrich=enrich_result,
            dry_run=dry_run,
            wrote_file=False,
        )

        if strict and match_result.unmatched_count > 0:
            return EnrichRunResult(
                summary=summary,
                wrote_file=False,
                strict_failed=True,
            )

        wrote_file = False
        if not dry_run and enrich_result.updated > 0:
            save_subsidy_array(json_path, records, backup=backup)
            wrote_file = True

        if map_out is not None and not dry_run:
            save_index_cache(
                map_out,
                index,
                entry_url=cache_entry_url,
            )
            log.info("Wrote index cache to %s", map_out)

        summary = format_enrich_run_summary(
            crawl=crawl_report,
            match=match_result,
            enrich=enrich_result,
            dry_run=dry_run,
            wrote_file=wrote_file,
        )
        return EnrichRunResult(summary=summary, wrote_file=wrote_file)
    finally:
        if own_client and http is not None:
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
    map_in: Path | None = typer.Option(
        None,
        "--map-in",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Load subsidy URL index from cache; skip live crawl.",
    ),
    map_out: Path | None = typer.Option(
        None,
        "--map-out",
        help="Write effective index cache after a successful run.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit with error when any JSON row does not match the index.",
    ),
    request_delay: float = typer.Option(
        0.0,
        "--request-delay",
        min=0.0,
        help="Seconds to wait after each HTTP response (live crawl only).",
    ),
    browser_fetch: bool = typer.Option(
        False,
        "--browser-fetch",
        help=(
            "Use curl-cffi TLS impersonation for live HTTP "
            "(requires `uv sync --extra browser`)."
        ),
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
            map_in=map_in,
            map_out=map_out,
            strict=strict,
            request_delay_seconds=request_delay,
            browser_fetch=browser_fetch,
        )
    except (
        CrawlError,
        DiscoveryError,
        JsonLoadError,
        JsonSaveError,
        MapCacheError,
    ) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result.summary, err=True)
    if result.strict_failed:
        raise typer.Exit(code=1)


@crawl_app.callback(invoke_without_command=True)
def crawl_cmd(
    ctx: typer.Context,
    map_out: Path = typer.Option(
        ...,
        "--map-out",
        help="Path to write the subsidy URL index cache (required).",
    ),
    entry_url: str = typer.Option(
        DEFAULT_ENTRY_URL,
        "--entry-url",
        help="Amsterdam subsidies overview URL for stadsdeel discovery.",
    ),
    request_delay: float = typer.Option(
        0.0,
        "--request-delay",
        min=0.0,
        help="Seconds to wait after each HTTP response.",
    ),
    browser_fetch: bool = typer.Option(
        False,
        "--browser-fetch",
        help=(
            "Use curl-cffi TLS impersonation for live HTTP "
            "(requires `uv sync --extra browser`)."
        ),
    ),
) -> None:
    """Run crawl when ``stadsdelen crawl --map-out PATH`` is invoked."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        result = run_crawl(
            map_out,
            entry_url=entry_url,
            request_delay_seconds=request_delay,
            browser_fetch=browser_fetch,
        )
    except (CrawlError, DiscoveryError, MapCacheError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result.summary, err=True)
