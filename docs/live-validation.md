# Live validation checklist

Manual sign-off before (or after) enriching **production** subsidies JSON with `stadsdelen`. CI does not run these steps.

Copy this checklist into your run notes and tick each item.

---

## 1. Local / CI parity

- [ ] Clone repo and `cd` into project root
- [ ] `uv sync --frozen`
- [ ] `uv run ruff check . && uv run ruff format --check .`
- [ ] `uv run pytest` (offline; matches GitHub Actions)

## 2. Optional network smoke (amsterdam.nl)

Skip if the site is unreachable; use a recent index cache for JSON work instead.

- [ ] `uv run pytest -m network tests/test_discovery.py` (entry-page discovery)
- [ ] `uv run pytest -m network tests/test_crawl.py::test_build_subsidy_index_live_smoke` (partial live crawl)

## 3. Data safety

- [ ] Work on a **copy** of the production JSON file, not the sole original
- [ ] Note full path to the copy: `________________________________`
- [ ] After a non–dry-run enrich, confirm `{name}.json.bak` exists (unless you used `--no-backup`)

## 4. Dry-run review

Using `--map-in` with a fresh or trusted cache **or** a live crawl dry-run:

- [ ] `uv run stadsdelen enrich --dry-run … path/to/copy.json`
- [ ] Record stderr counts: matched ______, unmatched ______, updated ______, skipped ______
- [ ] Review unmatched URLs; decide if acceptable or if you need `--strict` / site fixes
- [ ] If unmatched count is above zero and you require zero gaps, do **not** run without `--strict` until resolved

## 5. Crawl freshness (when using live HTTP)

- [ ] `uv run stadsdelen crawl --request-delay 0.5 --map-out cache/subsidy-index.json`
- [ ] stderr shows expected district count (≥ 7) and a reasonable indexed URL count
- [ ] Cache path noted: `________________________________`

## 6. Enrich

- [ ] `uv run stadsdelen enrich --map-in cache/subsidy-index.json path/to/copy.json` (or live enrich)
- [ ] Spot-check **3–5** rows:
  - [ ] Leading sentence matches `Stadsdeel: label1, label2.` (labels from crawl index)
  - [ ] Remainder of `markdown` unchanged aside from the prefix
  - [ ] Other JSON fields unchanged

## 7. Idempotency

- [ ] Re-run the same enrich command
- [ ] stderr reports `updated=0` (or equivalent) for unchanged rows
- [ ] File modification time unchanged if no updates were needed

## 8. Sign-off

| Field | Value |
|-------|--------|
| Date | |
| Operator | |
| JSON file (copy) | |
| Index cache (if used) | |
| Unmatched URL count | |
| Notes | |

---

See also the [Operator runbook](../README.md#operator-runbook) in the project README.
