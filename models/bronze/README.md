# Bronze

Raw-to-staged models. One `stg_` model per source, light typing/renaming only — no dedup, no unit conversion, no business logic. That happens in Silver.

Implemented models:
- `stg_sensor_readings.sql`
- `stg_shipment_events.sql`
- `stg_route_metadata.sql`
- `stg_product_master.sql`
- `stg_carrier_master.sql`
- `stg_shipments.sql` — not in the original spec's model list; added to carry shipment-level product/route/carrier references (see `data_generator/README.md` "Known gap").
- `stg_shipment_legs.sql` — same reason; carries the shipment-leg grain the Gold fact table is built at (spec §4.1).

Sources are declared in `_bronze__sources.yml`, pointing at a `raw` BigQuery dataset with one table per `data_generator/` output CSV. Column-level docs and generic tests (`unique`, `not_null`, `accepted_values`, `relationships`) live in `_bronze__models.yml`.

Not yet runnable — no BigQuery project or `profiles.yml` exists yet, and the raw CSVs from `data_generator/` haven't been loaded into BigQuery.
