# Cold-Chain Visibility & Spoilage Risk Analytics

An analytics engineering portfolio project: turns synthetic, deliberately noisy cold-chain sensor and shipment data into a tested star schema for tracking spoilage risk and estimated emissions at the shipment-leg level.

Full spec: [`docs/project_spec.md`](docs/project_spec.md).

## Architecture

Medallion architecture (Bronze → Silver → Gold) in dbt, on BigQuery:

- **Bronze** (`models/bronze/`) — staged raw sources, light typing only.
- **Silver** (`models/silver/`) — dedup, unit normalization, calibration-drift flagging, event sequencing.
- **Gold** (`models/gold/`) — star schema, one fact row per shipment leg, plus `dim_product`, `dim_route`, `dim_carrier`, `dim_date`.

See each folder's README for the planned models.

## Repo layout

```
data_generator/   synthetic sensor + shipment data generator (Python)
models/           dbt models: bronze/, silver/, gold/
tests/            singular (custom SQL) tests
seeds/            static reference data
macros/           dbt macros
.github/workflows/  CI: dbt build + test on every PR
docs/             project spec and design notes
```

## Status

Repo scaffold only — no models, generator, or CI logic implemented yet. See [`docs/project_spec.md`](docs/project_spec.md) §9 for the milestone sequence.

## Setup

Not yet functional. Once the data generator and dbt models exist, this section will cover: Python env setup, BigQuery sandbox project creation, `profiles.yml` configuration, and how to run `dbt build` locally.
