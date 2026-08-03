# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

Cold-Chain Visibility & Spoilage Risk Analytics — a dbt/BigQuery analytics engineering project. Full spec: `docs/project_spec.md`.

**Resuming a session? Read `docs/session_handoff.md` first** — it has current branch/PR state, what's implemented, decisions made and why, and open questions for the next milestone. Update it at the end of each work session.

Data generator (M2), Bronze staging models, Silver intermediate models, and Gold star schema are implemented. CI/CD and the dashboard are not yet implemented. See `docs/project_spec.md` §9 for the milestone sequence, and each `models/<layer>/README.md` for what's planned in that layer.

## Structure

- `data_generator/` — Python synthetic data generator, implemented. See `data_generator/README.md` for how each injected data quality issue works.
- `models/bronze/` — staging models, implemented (not yet runnable - no BigQuery project/`profiles.yml` and raw CSVs aren't loaded anywhere yet). Includes `stg_shipments`/`stg_shipment_legs`, added beyond the original spec's model list to carry shipment/leg identity - see `models/bronze/README.md`.
- `models/silver/` — intermediate models, implemented: dedup, unit normalization, calibration-drift flagging (heuristic, see `int_device_drift_flags.sql`), event sequencing. See `models/silver/README.md`.
- `models/gold/` — star schema, implemented: `fct_shipment_conditions` (one row per shipment leg) plus `dim_product`/`dim_route`/`dim_carrier`/`dim_date`. Null `product_id`/`route_id` are kept and mapped to an `'UNKNOWN'` dim member rather than excluded; drift-flagged readings are excluded from spoilage metrics with an `'unscoreable'` (null) fallback rather than a silent `false`. See `models/gold/README.md` and `docs/project_spec.md` §4.3 for full rationale.
- `tests/` — all 5 of the spec's singular tests implemented. See `tests/README.md`.
- `seeds/`, `macros/` — dbt seeds and macros.
- `.github/workflows/ci.yml` — PR-triggered dbt build (currently a skeleton; needs a `profiles.yml` CI target and repo secrets before it will actually run).

## Commands

- `python data_generator/generate.py --seed 42` — generate synthetic raw data into `data_generator/output/` (gitignored).

No `profiles.yml` or BigQuery project configured yet, so `dbt` commands aren't runnable. Update this section once those exist.
