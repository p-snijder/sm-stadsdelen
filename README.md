# sm-stadsdelen

Python tool to crawl Amsterdam **stadsdeel** subsidy overview pages, build a subsidy URL → districts index, and prepend a `Stadsdeel:` line to matching records in a user-provided JSON array. Full product scope lives in [`.cursor/plans/stadsdeel_subsidy_mapper_471919d0.plan.md`](.cursor/plans/stadsdeel_subsidy_mapper_471919d0.plan.md).

**Slice 1:** URL normalization (`stadsdelen.urls`).

**Slice 2:** Entry-page district discovery (`stadsdelen.discovery`).

**Slice 3:** District crawl and subsidy URL index (`stadsdelen.crawl`, `stadsdelen.index`).

**Slice 4:** JSON load, URL match against index, dry-run reporting (`stadsdelen.json_io`, `stadsdelen.match`, `stadsdelen.reporting`). **Slice 5:** idempotent `Stadsdeel:` markdown enrichment (`stadsdelen.markdown`). **Slice 6:** Typer CLI (`stadsdelen enrich`), atomic in-place JSON save with optional `.bak` backup. **Slice 7:** index cache (`--map-in` / `--map-out`), `stadsdelen crawl`, `--strict`, HTTP `--request-delay`, and `--verbose` logging.

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

## District crawl and index (slice 3)

After discovery, crawl each stadsdeel overview page and build **`UrlToDistrictsIndex`**: normalized subsidy detail URL → sorted stadsdeel labels.

API:

- `build_subsidy_index(district_pages)` — HTTP crawl all districts, merge multi-district URLs, return `(index, CrawlReport)`.
- `parse_subsidy_links(html, page_url=...)` — pure parser for one listing page (`.resultaten .resultaat h2.link a`).
- `parse_pagination_next_url(html, page_url=...)` — follow `a.startagain` (“Volgende”) links.
- `crawl_district_subsidy_urls(district, client=...)` — one district including pagination.

**Labels:** Index entries use `DistrictPage.label` from discovery (e.g. anchor text **Subsidies Centrum**).

**Pagination (master-plan question #3):** District listings that exceed one page expose the next page via **`a.startagain`**. Because URL normalization strips query strings, pagination must use **path-based** next URLs (not `?page=2`). Offline tests use recorded-style fixtures under [`tests/fixtures/html/`](tests/fixtures/html/) (`district-centrum.html`, `district-noord.html`, `district-zuid-page1.html` / `page2`). Automated httpx recording often gets HTTP 403 on district URLs; save HTML from a browser when needed.

Record or refresh a district fixture:

```bash
uv run python scripts/record_district_html.py \
  --district-url "https://www.amsterdam.nl/subsidies/centrum/" \
  --slug centrum
```

Optional live crawl smoke (first two discovered districts):

```bash
uv run pytest -m network tests/test_crawl.py::test_build_subsidy_index_live_smoke
```

### Slice 3 acceptance

- [x] Fixture-based parser tests for ≥ two districts (`uv run pytest`).
- [x] Pagination covered via two-page zuid fixtures + `startagain` parser.
- [x] Same subsidy URL on two districts yields two labels in the index.
- [x] `CrawlReport.by_district` exposes per-district link counts.

## JSON load and match (slice 4)

Load a user JSON **array** and match each object’s `url` to a `UrlToDistrictsIndex` (from crawl or tests). **No `markdown` changes and no file write** in this slice—slice 5 enriches; slice 6 saves in place.

**Required fields:** each object must have string `url` and string `markdown`. All other keys are preserved on load.

**Sample fixture:** [`tests/fixtures/json/subsidies-sample.json`](tests/fixtures/json/subsidies-sample.json) (synthetic URLs aligned with slice 3 HTML fixtures).

API:

- `load_subsidy_array(path)` — validate array; raise `JsonLoadError` on invalid input.
- `match_subsidies(records, index)` — normalize JSON URLs with `urls.normalize`, lookup index keys.
- `match_subsidies_file(json_path, index)` — load + match; returns `(records, MatchResult)`.
- `format_match_report(result)` — human-readable matched/unmatched summary for dry-run.

**Unmatched rows:** `not_in_index` when normalization succeeds but the URL is absent from the index; `normalize_failed` when `url` cannot be normalized. Unmatched URLs are reported, not fatal (unless a future `--strict` flag).

### Slice 4 acceptance

- [x] Invalid JSON / non-array / missing `url` or `markdown` fails fast with clear `JsonLoadError`.
- [x] Unmatched URLs listed; matched count correct on synthetic fixture (`uv run pytest`).
- [x] No output file write; matching is side-effect free on disk.

## Markdown enrichment (slice 5)

For rows matched to the index, prepend or update a leading **Stadsdeel** sentence on `markdown`. Updates happen **in memory only**—slice 6 writes the JSON file in place.

**Prefix format:** `Stadsdeel: {label1}, {label2}.` as the first sentence, then `\n\n` before the existing body when prepending. Labels use the same strings as the crawl index (e.g. `Subsidies Centrum`).

**Idempotency:** If the leading sentence already lists the same district set (order ignored), the field is unchanged. If the set differs, only the prefix sentence is replaced; the body remainder is preserved.

API:

- `update_markdown(markdown, districts)` — pure single-field update; returns `(new_markdown, MarkdownUpdateStatus)`.
- `enrich_matched_rows(records, match_result)` — mutate matched rows only; returns `EnrichResult`.
- `enrich_subsidies(records, index)` — `match_subsidies` + `enrich_matched_rows`.
- `format_enrich_report(enrich_result)` — updated vs skipped counts for dry-run (slice 6).

### Slice 5 acceptance

- [x] First run prepends correct sentence on matched rows (`uv run pytest`).
- [x] Second run unchanged (idempotent).
- [x] District set change replaces prefix only (see `tests/test_markdown.py`).
- [x] Objects without index entry unchanged (`tests/test_enrich.py`).
- [x] No file write in this slice.

## CLI and in-place save (slice 6)

Run the full pipeline (live crawl of amsterdam.nl by default, then match, enrich, save):

```bash
uv run stadsdelen enrich path/to/subsidies.json
```

Put flags **before** the JSON path (Typer option ordering):

```bash
uv run stadsdelen enrich --dry-run path/to/subsidies.json
uv run stadsdelen enrich --no-backup path/to/subsidies.json
uv run stadsdelen enrich --entry-url 'https://www.amsterdam.nl/subsidies/subsidies-onderwerp/' path/to/subsidies.json
```

| Flag | Behavior |
|------|----------|
| `--dry-run` | Crawl and enrich in memory; print summary to stderr; **no file write**. |
| `--no-backup` | Skip copying the input file to `{name}.json.bak` before overwrite (backup is **on** by default). |
| `--entry-url` | Entry page for stadsdeel discovery (default: subsidies-onderwerp URL). |

**Write rules:** The JSON file is updated **in place** with `indent=2` (whitespace may change). If no matched row needs a markdown update (`updated == 0`), the file is not rewritten. On failure during save, the original file is left intact (atomic temp + rename).

**Reporting:** Crawl, match, and enrich counts are printed to **stderr** after each run.

### Slice 6 acceptance

- [x] `--dry-run` performs no write and reports would-update counts.
- [x] Backup created by default before overwrite; `--no-backup` disables.
- [x] E2E test with mocked HTTP + fixture JSON (`tests/test_cli_e2e.py`).
- [x] stderr summary includes districts, indexed URLs, matched/unmatched, updated/skipped.

## Map cache and operational hardening (slice 7)

Two-phase workflow: crawl once (live HTTP), enrich JSON offline with the saved index.

```bash
uv run stadsdelen crawl --map-out cache/subsidy-index.json
uv run stadsdelen enrich --map-in cache/subsidy-index.json path/to/subsidies.json
```

You can still run a single live `enrich` without a cache (slice 6 behavior). Optional `--map-out` on `enrich` writes the **effective** index after a successful non-dry-run (from crawl or from `--map-in`).

### Index cache format (version 1)

| Field | Meaning |
|-------|---------|
| `version` | Must be `1` |
| `generated_at` | UTC ISO8601 timestamp when written |
| `entry_url` | Optional; entry page used when the index was crawled |
| `index` | Object: normalized subsidy URL → array of stadsdeel label strings |

Example fixture: [`tests/fixtures/json/subsidy-index-v1.json`](tests/fixtures/json/subsidy-index-v1.json). API: `load_index_cache`, `save_index_cache` in [`stadsdelen.map_cache`](src/stadsdelen/map_cache.py).

### Additional CLI flags

Shared on **`stadsdelen crawl`** and **`stadsdelen enrich`** (place before subcommand arguments):

| Flag | Behavior |
|------|----------|
| `--verbose` | INFO logs from the `stadsdelen` logger |
| `--log-level` | `warning`, `info`, or `debug` (overrides `--verbose`) |
| `--request-delay SECONDS` | Pause after each HTTP response during live crawl (default `0`; try `0.3–1.0` on amsterdam.nl) |

**`stadsdelen crawl`** (requires `--map-out`):

| Flag | Behavior |
|------|----------|
| `--map-out PATH` | Write version-1 index cache (required) |
| `--entry-url` | Same as enrich |

**`stadsdelen enrich`** (extends slice 6):

| Flag | Behavior |
|------|----------|
| `--map-in PATH` | Load index from cache; **no HTTP** |
| `--map-out PATH` | Write index cache after success (skipped on `--dry-run`) |
| `--strict` | Exit code 1 if any JSON row is unmatched (`not_in_index` or `normalize_failed`); no JSON write |

When `--map-in` is set, `--entry-url` does not trigger a crawl (only used as metadata if you also write `--map-out` after a live crawl).

### Slice 7 acceptance

- [x] `stadsdelen crawl --map-out` builds cache from mocked/live crawl.
- [x] `enrich --map-in` skips discovery/crawl and matches fixture cache.
- [x] E2E: crawl → map-in enrich equals live enrich on same JSON (`tests/test_cli_e2e.py`).
- [x] `--strict` fails before write when unmatched rows remain.
- [x] `--dry-run` does not write JSON or `--map-out` cache.

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
