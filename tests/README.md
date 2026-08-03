# Singular tests

Custom SQL tests, one file per assertion. Generic tests (unique, not_null, relationships, accepted_values) live in each model's `schema.yml` instead.

## Implemented (spec §6.2)

- `assert_no_rapid_fire_duplicates_post_dedup.sql` — no two readings from the same device+leg remain within 60 seconds of each other after `int_sensor_readings_deduped`.
- `assert_unit_normalization_correct.sql` — every row's `temperature_value_c` matches the correct conversion of its original value, not just present.
- `assert_event_sequencing_preserves_row_count.sql` — `stg_shipment_events` and `int_shipment_events_sequenced` have identical row counts, proving events are reordered, not dropped.

- `assert_drift_flagged_legs_unscoreable.sql` — a leg with zero clean (non-drift-flagged) readings gets `spoilage_risk_flag = null` ("unscoreable"), never `true`/`false`. Implements the spec's "drift-flagged sensors excluded from spoilage calculations" once Gold's exclusion rule was decided — see `docs/project_spec.md` §4.3.
- `assert_missing_metadata_resolved_consistently.sql` — implements the spec's "every shipment leg has a non-null route and carrier reference" once the Gold business rule was decided: legs are kept (not dropped) with an `'UNKNOWN'` surrogate key, so this asserts no raw nulls leak into `fct_shipment_conditions` and `has_missing_metadata` agrees with which rows got substituted.
