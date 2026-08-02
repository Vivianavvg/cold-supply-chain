# Session handoff

Working notes so a new session can pick this project up without re-deriving context. Update this file at the end of each work session rather than trusting memory across sessions.

## Project

Cold-Chain Visibility & Spoilage Risk Analytics — dbt/BigQuery portfolio project. Full spec: `docs/project_spec.md` (transcribed from the original `.docx`; some spec tables were header-only in the source doc and are marked `TBD`).

Repo: https://github.com/Vivianavvg/cold-supply-chain (owner: Vivianavvg)

## Workflow being followed

Feature branch → push → open PR on github.com → user merges via the web UI → pull `main` locally → delete the merged local branch → branch again for the next milestone. `gh` CLI is **not installed** on this machine, so PRs must be opened/merged manually on github.com; Claude can push branches and give the PR URL but cannot merge.

`.github/workflows/ci.yml` will show **all checks failed** on every PR — this is expected and fine to ignore/merge through. It's a placeholder from the initial scaffold that references a BigQuery service account and `profiles.yml` `ci` target that don't exist yet. Real CI/CD is its own milestone (spec §7), planned after Gold.

## Status as of this handoff

| Milestone | Branch | State |
|---|---|---|
| Repo scaffold | `main` | Merged |
| M2: Data generator | `main` (was `feature/data-generator`) | Merged |
| Bronze staging models | `main` (was `feature/bronze-models`) | Merged |
| Silver intermediate models + 3 tests | `main` (was `feature/silver-models`) | Merged (PR #3) |
| Gold star schema | — | Not started — design decisions made, see below |
| CI/CD (real) | — | Not started |
| Dashboard | — | Not started |

**Next action when resuming:** branch `feature/gold-models` off `main` and start implementing Gold using the decisions below.

**Note on this handoff doc's history:** this file's original commit (`fc1ba2f`) was made *after* PR #3 had already been merged, so it never made it into `main` via that PR — it sat orphaned on `feature/silver-models` until cherry-picked directly onto `main` in a later session. If a future PR merge seems to "lose" doc-only commits made close to merge time, check for the same race — commits pushed after a PR merges don't ride along.

## What exists and why (decisions made along the way)

- **`data_generator/`** (Python, `generate.py` + `config.py`) — produces 7 raw CSVs (products, carriers, routes, shipments, shipment_legs, sensor_readings, shipment_events) into `data_generator/output/` (gitignored, regenerate with `python generate.py --seed 42`). Injects all 6 data quality problems from spec §3.1 and writes a `data_quality_summary.txt` with exact injected counts per run, so downstream tests can be checked against known-true numbers.
- **Known gap vs. spec §5**: the spec's Bronze model list names 5 staging models but none for shipment/leg identity. Added `stg_shipments` and `stg_shipment_legs` beyond the spec's list — necessary because the Gold grain (one row per shipment leg, spec §4.1) needs an upstream source for it. Documented in `data_generator/README.md` and `models/bronze/README.md`.
- **`models/bronze/`** — 7 staging models (5 spec-named + the 2 above), light rename/type-cast only. Sources declared in `_bronze__sources.yml` against a `raw` BigQuery dataset (doesn't exist yet). Generic tests (unique/not_null/accepted_values/relationships) in `_bronze__models.yml`. `stg_shipments.product_id`/`route_id` are deliberately **not** `not_null`-tested — nulls there are the intentional spec §3.1 injection, not a bug.
- **`models/silver/`** — dedup (`int_sensor_readings_deduped`, LAG-based comparison rather than fixed time-bucket rounding, to avoid splitting a genuine reading pair that straddles a bucket boundary), unit normalization (`int_sensor_readings_normalized`, keeps original value+unit for audit), calibration-drift flagging (`int_device_drift_flags` + `int_sensor_readings_drift_flagged`), event sequencing (`int_shipment_events_sequenced`, orders by true `event_ts` not arrival order).
  - `int_device_drift_flags` is **not in the spec's model list** — added because the drift-flagged model needs a per-device verdict from somewhere. It's a **statistical heuristic, not ground truth**: flags a device if its average deviation from the product's safe-range midpoint is ≥1.5°C across ≥3 legs. Real pipelines don't have ground truth for this either. Verified against real generator output (via DuckDB, since no BigQuery project exists to run actual `dbt`): 22/199 devices flagged vs. ~20 true drifted devices — reasonable but not exact.
- **No BigQuery project, no `profiles.yml` exist yet** — nothing in `models/` has actually been run through `dbt`. All SQL has instead been sanity-checked by hand-translating the logic into DuckDB against real generator output (dedup count matched the exact injected duplicate count, zero normalization violations, exact row-count parity on event sequencing). This should still happen for real once a BigQuery sandbox is set up — don't assume DuckDB verification is equivalent to `dbt build` passing.
- **Tests**: 3 of the spec's 5 singular tests (§6.2) are written — dedup effectiveness, normalization correctness, event row-count parity. The other 2 (drift-exclusion from spoilage calc, non-null route/carrier per leg) need Gold to exist first; noted in `tests/README.md`.

## Gold design decisions (made 2026-08-01, not yet implemented)

- **Null `product_id`/`route_id` (spec §3.1 injection, ~3% of shipments):** kept in `fct_shipment_conditions`, not excluded. Map to an `'UNKNOWN'` surrogate member in `dim_product`/`dim_route` (Kimball pattern), and add a `has_missing_metadata` flag on the fact row. Rationale: excluding would silently under-report shipment volume, and since `product_id` is what determines the safe temp range, dropping these legs would make exactly the shipments most worth checking invisible instead of flagged. Full writeup in `docs/project_spec.md` §4.3.
- **`spoilage_risk_flag` vs. drift-flagged readings (spec §6.2):** readings where `int_sensor_readings_drift_flagged.is_drift_flagged = true` are excluded entirely from the `minutes_out_of_range`/`max_temp_deviation_c` calc (not down-weighted, not counted as-is) — a biased device could otherwise push a leg over/under the risk threshold on bad data. Fact row carries `has_drift_affected_readings` (or `pct_readings_drift_flagged`) so the exclusion is visible. If a leg has zero clean readings left after exclusion, `spoilage_risk_flag` is `NULL`/`'unscoreable'`, not `false` — "no valid data" must not read as "confirmed safe." Same principle as the null-metadata decision above. Full writeup in `docs/project_spec.md` §4.3.
- Both decisions above now unblock the 2 deferred singular tests noted below (drift-exclusion, non-null route/carrier) — update `tests/README.md` when those are written against the actual Gold SQL.

## Still open

- `estimated_emissions_kg` formula — spec §4.3 says "derived from distance, transport mode, and fuel type" but doesn't give the formula. `carriers.emissions_factor_kg_co2_per_km` exists in the generator output as a starting point.

## Environment notes

- No `gh` CLI on this machine (checked both Bash and PowerShell) — PRs are manual via github.com.
- `pandas`, `Faker`, `duckdb` are installed in whatever Python `python3` resolves to on this machine (Windows Store Python). `duckdb` isn't in `requirements.txt` — it's a local verification tool only, not a project dependency.
