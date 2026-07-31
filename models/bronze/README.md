# Bronze

Raw-to-staged models. One `stg_` model per source, light typing/renaming only — no dedup, no unit conversion, no business logic.

Planned models (see spec §5, §3):
- `stg_sensor_readings.sql`
- `stg_shipment_events.sql`
- `stg_route_metadata.sql`
- `stg_product_master.sql`
- `stg_carrier_master.sql`

Not yet implemented — depends on the data generator (`data_generator/`) producing raw tables/files to source from.
