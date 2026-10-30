# sm-stadsdelen

Python tool to crawl Amsterdam **stadsdeel** subsidy overview pages, build a subsidy URL → districts index, and prepend a `Stadsdeel:` line to matching records in a user-provided JSON array. Full product scope lives in [`.cursor/plans/stadsdeel_subsidy_mapper_471919d0.plan.md`](.cursor/plans/stadsdeel_subsidy_mapper_471919d0.plan.md).

**Slice 1 status:** URL normalization only. HTTP crawl, JSON enrichment, and CLI are not implemented yet.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Python 3.11+ (see `.python-version`)

## Development

```bash
uv sync
uv run pytest
```

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
