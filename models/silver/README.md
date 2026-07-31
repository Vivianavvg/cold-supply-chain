# Silver

Cleans up the data quality problems injected in the generator (spec §3.1): dedup, unit normalization, calibration-drift flagging, event sequencing. Sensor-level grain lives here — the Gold layer rolls it up.

Planned models (see spec §5):
- `int_sensor_readings_deduped.sql`
- `int_sensor_readings_normalized.sql`
- `int_sensor_readings_drift_flagged.sql`
- `int_shipment_events_sequenced.sql`

Not yet implemented — depends on Bronze staging models.
