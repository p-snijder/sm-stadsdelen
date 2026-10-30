#!/usr/bin/env python3
"""Record entry-page HTML for offline parser tests.

Uses a browser-like httpx session (warm-up GETs + cookies) before fetching
the subsidies-onderwerp overview page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stadsdelen.discovery import parse_district_pages
from stadsdelen.http import (
    create_client,
    is_blocked_or_error_page,
    warm_session,
)

DEFAULT_ENTRY = "https://www.amsterdam.nl/subsidies/subsidies-onderwerp/"
DEFAULT_OUTPUT = Path("tests/fixtures/html/entry-subsidies-onderwerp.html")

WARMUP_URLS = (
    "https://www.amsterdam.nl/",
    "https://www.amsterdam.nl/subsidies/",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-url", default=DEFAULT_ENTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with create_client(timeout=30.0) as client:
        warm_session(client, WARMUP_URLS)
        response = client.get(args.entry_url)
        text = response.text

    if is_blocked_or_error_page(response, text):
        print(
            f"Blocked or error page for {args.entry_url} "
            f"(HTTP {response.status_code}).",
            file=sys.stderr,
        )
        print(
            "Save HTML manually from a browser into "
            f"{args.output} and re-run tests.",
            file=sys.stderr,
        )
        return 1

    pages = parse_district_pages(text, page_url=str(response.url))
    if len(pages) < 7:
        print(
            f"Only {len(pages)} district links parsed; expected at least 7.",
            file=sys.stderr,
        )
        return 1

    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output} ({len(text)} bytes, {len(pages)} districts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
