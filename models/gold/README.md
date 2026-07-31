# Gold

Star schema. Fact grain is one row per shipment leg (spec §4.1), not one row per sensor reading.

Planned models (see spec §5):
- `fct_shipment_conditions.sql`
- `dim_product.sql`
- `dim_route.sql`
- `dim_carrier.sql`
- `dim_date.sql`

Key derived metrics on the fact table (spec §4.3): `minutes_out_of_range`, `max_temp_deviation_c`, `spoilage_risk_flag`, `estimated_emissions_kg`.

Not yet implemented — depends on Silver models.
