#!/usr/bin/env python3
"""Record a district overview HTML fixture for offline crawl tests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stadsdelen.crawl import parse_subsidy_links
from stadsdelen.discovery import WARMUP_URLS
from stadsdelen.http import create_client, is_blocked_or_error_page, warm_session

DEFAULT_OUTPUT_DIR = Path("tests/fixtures/html")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--district-url",
        required=True,
        help="District overview URL, e.g. https://www.amsterdam.nl/subsidies/centrum/",
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Fixture basename slug, e.g. centrum -> district-centrum.html",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--min-links",
        type=int,
        default=1,
        help="Minimum subsidy links parse_subsidy_links must find",
    )
    args = parser.parse_args()

    output = args.output_dir / f"district-{args.slug}.html"
    output.parent.mkdir(parents=True, exist_ok=True)

    with create_client(timeout=30.0) as client:
        warm_session(client, WARMUP_URLS)
        response = client.get(args.district_url)
        text = response.text

    if is_blocked_or_error_page(response, text):
        print(
            f"Blocked or error page for {args.district_url} "
            f"(HTTP {response.status_code}).",
            file=sys.stderr,
        )
        print(
            f"Save HTML manually from a browser into {output} and re-run tests.",
            file=sys.stderr,
        )
        return 1

    page_url = str(response.url)
    links = parse_subsidy_links(text, page_url=page_url)
    if len(links) < args.min_links:
        print(
            f"Only {len(links)} subsidy links parsed; "
            f"expected at least {args.min_links}.",
            file=sys.stderr,
        )
        return 1

    output.write_text(text, encoding="utf-8")
    print(
        f"Wrote {output} ({len(text)} bytes, {len(links)} subsidy links).",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
