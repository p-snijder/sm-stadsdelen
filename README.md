# sm-stadsdelen

Python tool to crawl Amsterdam **stadsdeel** subsidy overview pages, build a subsidy URL → districts index, and prepend a `Stadsdeel:` line to matching records in a user-provided JSON array. Full product scope lives in [`.cursor/plans/stadsdeel_subsidy_mapper_471919d0.plan.md`](.cursor/plans/stadsdeel_subsidy_mapper_471919d0.plan.md).

**Slice 1:** URL normalization (`stadsdelen.urls`).

**Slice 2:** Entry-page district discovery (`stadsdelen.discovery`). JSON enrichment and CLI are not implemented yet.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Python 3.11+ (see `.python-version`)

## Development

```bash
uv sync
uv run pytest
```

Offline tests exclude live HTTP by default. To run the optional smoke test against amsterdam.nl:

```bash
uv run pytest -m network
```

## District discovery (slice 2)

Default entry URL:

`https://www.amsterdam.nl/subsidies/subsidies-onderwerp/`

**Where stadsdeel links live:** On that page, district overview links appear in the main content sidebar under the heading **“Per stadsdeel/-gebied”** (not in the topic grid). Each link targets `/subsidies/{stadsdeel}/` (Weesp uses `/subsidies/subsidies-stadsgebied-weesp/`).

API:

- `discover_district_pages(entry_url)` — HTTP fetch, parse, validate (≥ 7 districts).
- `parse_district_pages(html, page_url=...)` — pure HTML parser (used in tests).

Recorded HTML for CI lives in [`tests/fixtures/html/entry-subsidies-onderwerp.html`](tests/fixtures/html/entry-subsidies-onderwerp.html). Refresh it with:

```bash
uv run python scripts/record_entry_html.py
```

The recorder uses a browser-like httpx session (warm-up requests + cookies). If amsterdam.nl returns HTTP 403 or **“Er is iets mis gegaan”**, save the page from a normal browser into the fixture path above and commit the file.

**Fallback:** Set `STADSDELEN_DISTRICT_FALLBACK=1` or pass `allow_fallback=True` to use the built-in canonical district URL list when parsing finds too few links (last resort; default off).

### Slice 2 acceptance

- [x] Fixture-based parser tests pass without network (`uv run pytest`).
- [x] `discover_district_pages` mocked HTTP integration tests pass.
- [x] Optional `@pytest.mark.network` smoke test documented (`uv run pytest -m network`).
- [x] Entry-page link source documented (sidebar **Per stadsdeel/-gebied**).

## URL normalization

The `stadsdelen.urls.normalize` and `resolve` functions canonicalize URLs so crawled links and JSON `url` fields match reliably.

| Rule | Behavior |
|------|----------|
| Scheme | `http` → `https` |
| Host | Lowercase; `amsterdam.nl` → `www.amsterdam.nl` |
| Fragment | Removed |
| Query | Removed entirely (v1) |
| Path | Duplicate slashes collapsed; path lowercased |
| Trailing slash | Stripped except for root `/` |
| Relative URLs | Use `resolve(href, base_url)` or `normalize(href, base=base_url)` |

Invalid or relative URLs without a base raise `ValueError`.
