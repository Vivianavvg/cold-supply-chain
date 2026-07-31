# Data generator

Produces synthetic cold-chain sensor and shipment data as raw CSVs, with the data quality problems from spec §3.1 deliberately injected: sensor dropout, duplicate rapid-fire readings, calibration drift, °C/°F unit mismatch, out-of-sequence delivery events, and missing product/route references.

## Run

```
pip install -r ../requirements.txt
python generate.py --seed 42
```

Writes to `output/` (gitignored — regenerate rather than commit):

- `products.csv`, `carriers.csv`, `routes.csv` — reference/master data
- `shipments.csv` — shipment header, `product_id`/`route_id` sometimes null (§3.1)
- `shipment_legs.csv` — one row per shipment leg (device assignment, planned distance, leg start/end)
- `sensor_readings.csv` — per-leg temperature readings at `config.READING_INTERVAL_MINUTES` cadence
- `shipment_events.csv` — `picked_up` / `arrived_checkpoint` / `delivered` events per leg
- `data_quality_summary.txt` — exact counts of each injected issue for this run, so Silver/test work can be checked against known-true numbers instead of re-deriving them

Injection rates are tunable in `config.py`. Pass `--shipments N` to change volume, `--seed` for reproducibility.

## How each §3.1 issue is simulated

- **Sensor dropout** — a fraction of expected readings are silently skipped (`DROPOUT_RATE`).
- **Duplicate rapid-fire readings** — a fraction of readings get a near-identical duplicate 1-10 seconds later (`DUPLICATE_RATE`).
- **Calibration drift** — a fraction of devices have a persistent +2 to +4°C offset applied to every reading they produce (`DRIFT_DEVICE_RATE`).
- **Unit inconsistency** — a fraction of devices report Fahrenheit instead of Celsius, consistently (`FAHRENHEIT_DEVICE_RATE`).
- **Out-of-sequence events** — for a fraction of shipments, the `delivered` event's `ingested_at` is set earlier than the true `event_ts` and earlier than the final leg's own sensor readings' `ingested_at`, simulating network lag between systems (`OUT_OF_SEQUENCE_RATE`). `event_ts`/`reading_ts` stay chronologically correct — only arrival order is broken, which is what a sequencing step needs to fix.
- **Missing product/route references** — a fraction of shipments get a null `product_id` or `route_id` in `shipments.csv` (`MISSING_METADATA_RATE`). The underlying physical temperature data is still generated using the true (uncorrupted) product safe range, since the injected problem is a broken reference, not physically implausible readings.

## Known gap vs. the original spec

Spec §5 lists five Bronze staging models but none for shipment/leg identity. `shipments.csv` and `shipment_legs.csv` exist here because the Gold grain (one row per shipment leg, §4.1) and the referential-integrity test (§6.2, non-null route/carrier per leg) both require an upstream source for that identity. Resolved in Bronze via `stg_shipments` / `stg_shipment_legs` — see `models/bronze/README.md`.
