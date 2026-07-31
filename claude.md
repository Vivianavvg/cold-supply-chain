# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

Cold-Chain Visibility & Spoilage Risk Analytics — a dbt/BigQuery analytics engineering project. Full spec: `docs/project_spec.md`.

Currently at the repo-scaffold stage: folder structure and config exist, but the data generator, dbt models, tests, and CI logic are not yet implemented. See `docs/project_spec.md` §9 for the milestone sequence, and each `models/<layer>/README.md` for what's planned in that layer.

## Structure

- `data_generator/` — Python synthetic data generator (not yet implemented).
- `models/bronze/`, `models/silver/`, `models/gold/` — dbt models, one folder per Medallion layer.
- `tests/` — singular (custom SQL) dbt tests.
- `seeds/`, `macros/` — dbt seeds and macros.
- `.github/workflows/ci.yml` — PR-triggered dbt build (currently a skeleton; needs a `profiles.yml` CI target and repo secrets before it will actually run).

## Commands

Not yet applicable — no `profiles.yml`, no BigQuery project configured, no generator output to build from. Update this section once those exist (expect: `dbt deps`, `dbt build`, `dbt test`, and a generator invocation command).
