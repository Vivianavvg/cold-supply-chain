# Gold

Star schema. Fact grain is one row per shipment leg (spec §4.1), not one row per sensor reading.

Implemented:
- `fct_shipment_conditions.sql` — one row per shipment leg.
- `dim_product.sql`, `dim_route.sql` — real rows plus an `'UNKNOWN'` surrogate member for shipments with null `product_id`/`route_id` (spec §3.1 injection).
- `dim_carrier.sql` — real rows only; `carrier_id` is never null in the source data, so no `'UNKNOWN'` member.
- `dim_date.sql` — date spine (`dbt_utils.date_spine`) covering every date from the earliest `ship_date` to the latest `leg_end_ts`.

Key derived metrics on the fact table (spec §4.3):
- `minutes_out_of_range`, `max_temp_deviation_c` — computed only from readings where `is_drift_flagged = false`. A drift-flagged reading's own interval is dropped, not reassigned to a neighbor.
- `spoilage_risk_flag` — `true` when `minutes_out_of_range` exceeds `var('spoilage_risk_minutes_threshold')` (dbt_project.yml, default 30 per spec's example), `false` when under, `null` ("unscoreable") when a leg has zero clean readings to judge.
- `estimated_emissions_kg` — `planned_distance_km * carriers.emissions_factor_kg_co2_per_km`. Deliberately doesn't factor in `transport_mode` — the generator doesn't tie an emissions multiplier to it (only to leg speed/duration), so inventing one would be a fabricated number, not a derived one. See `docs/project_spec.md` §4.3.

Both the null-metadata and drift-exclusion decisions are documented in full, with rationale, in `docs/project_spec.md` §4.3 and `docs/session_handoff.md`.

Not yet run through real `dbt` — no BigQuery project/`profiles.yml` exist yet (same caveat as Bronze/Silver). Sanity-checked by hand-translating the SQL into DuckDB against real generator output; see session handoff for results.
