# Singular tests

Custom SQL tests, one file per assertion. Generic tests (unique, not_null, relationships, accepted_values) live in each model's `schema.yml` instead.

## Implemented (spec §6.2)

- `assert_no_rapid_fire_duplicates_post_dedup.sql` — no two readings from the same device+leg remain within 60 seconds of each other after `int_sensor_readings_deduped`.
- `assert_unit_normalization_correct.sql` — every row's `temperature_value_c` matches the correct conversion of its original value, not just present.
- `assert_event_sequencing_preserves_row_count.sql` — `stg_shipment_events` and `int_shipment_events_sequenced` have identical row counts, proving events are reordered, not dropped.

## Deferred to Gold

Two tests from the spec's list need the fact table to exist before they're meaningful:

- **Drift-flagged sensors excluded from spoilage calculations** — `int_device_drift_flags` (Silver) produces the verdict; the exclusion happens in `fct_shipment_conditions` (Gold), so the test belongs there.
- **Every shipment leg has a non-null route and carrier reference** — `stg_shipments.route_id`/`product_id` are deliberately nullable (spec §3.1). The business rule for what happens to those legs by the time they reach Gold (excluded? defaulted?) isn't decided yet - write this test once that's decided.
