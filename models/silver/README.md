# Silver

Cleans up the data quality problems injected in the generator (spec §3.1): dedup, unit normalization, calibration-drift flagging, event sequencing. Sensor-level grain lives here — the Gold layer rolls it up.

Implemented models:
- `int_sensor_readings_deduped.sql`
- `int_sensor_readings_normalized.sql`
- `int_sensor_readings_drift_flagged.sql`
- `int_shipment_events_sequenced.sql`
- `int_device_drift_flags.sql` — not in the original spec's model list; added because `int_sensor_readings_drift_flagged` needs a per-device verdict computed somewhere. It's a statistical heuristic (average deviation from the product's safe-range midpoint), not ground truth — see the model's SQL comment for its known limitations.

Column docs and generic tests live in `_silver__models.yml`. Corresponding singular tests live in `tests/` — see `tests/README.md` for which spec §6.2 tests are implemented here vs. deferred to Gold.

Not yet runnable — same reason as Bronze: no BigQuery project or `profiles.yml` exists yet.
