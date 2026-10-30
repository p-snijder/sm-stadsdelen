"""Typer CLI for stadsdeel subsidy enrichment."""

import typer

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Crawl Amsterdam stadsdeel subsidy pages and enrich JSON records.",
)
