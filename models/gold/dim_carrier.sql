-- No 'UNKNOWN' member here (unlike dim_product/dim_route) - the spec 3.1
-- missing-metadata injection only ever nulls product_id/route_id on
-- shipments, never carrier_id.
select
    carrier_id,
    carrier_name,
    fuel_type,
    emissions_factor_kg_co2_per_km
from {{ ref('stg_carrier_master') }}
