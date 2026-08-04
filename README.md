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

Data generator, Bronze/Silver/Gold models, and CI (`.github/workflows/ci.yml`, dbt build + test on every PR against an isolated per-PR BigQuery dataset) are implemented and verified against a real BigQuery project. The dashboard is not yet implemented. See [`docs/project_spec.md`](docs/project_spec.md) §9 for the milestone sequence and [`docs/session_handoff.md`](docs/session_handoff.md) for current in-progress state.

## Setup

```
pip install -r requirements.txt
python data_generator/generate.py --seed 42
```

See [`data_generator/README.md`](data_generator/README.md) for output details and tunable injection rates.

Running `dbt build` for real requires a BigQuery project and a service-account keyfile referenced from `~/.dbt/profiles.yml` (not committed — see `docs/session_handoff.md`'s "BigQuery sandbox setup" section for how it was set up). Once that exists, load the generated CSVs into the `raw` dataset with `data_generator/load_to_bigquery.py`, then run `dbt build`.
