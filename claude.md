# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

Cold-Chain Visibility & Spoilage Risk Analytics — a dbt/BigQuery analytics engineering project. Full spec: `docs/project_spec.md`.

Data generator (M2) and Bronze staging models are implemented. Silver, Gold, tests, and CI logic are not yet implemented. See `docs/project_spec.md` §9 for the milestone sequence, and each `models/<layer>/README.md` for what's planned in that layer.

## Structure

- `data_generator/` — Python synthetic data generator, implemented. See `data_generator/README.md` for how each injected data quality issue works.
- `models/bronze/` — staging models, implemented (not yet runnable - no BigQuery project/`profiles.yml` and raw CSVs aren't loaded anywhere yet). Includes `stg_shipments`/`stg_shipment_legs`, added beyond the original spec's model list to carry shipment/leg identity - see `models/bronze/README.md`.
- `models/silver/`, `models/gold/` — dbt models. Not yet implemented.
- `tests/` — singular (custom SQL) dbt tests. Not yet implemented.
- `seeds/`, `macros/` — dbt seeds and macros.
- `.github/workflows/ci.yml` — PR-triggered dbt build (currently a skeleton; needs a `profiles.yml` CI target and repo secrets before it will actually run).

## Commands

- `python data_generator/generate.py --seed 42` — generate synthetic raw data into `data_generator/output/` (gitignored).

No `profiles.yml` or BigQuery project configured yet, so `dbt` commands aren't runnable. Update this section once those exist.
