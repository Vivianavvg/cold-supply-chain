-- 'UNKNOWN' surrogate member for shipments with a null route_id (spec 3.1
-- injection) - same pattern as dim_product, see docs/project_spec.md 4.3.
select
    route_id,
    origin,
    destination,
    transport_mode,
    distance_km
from {{ ref('stg_route_metadata') }}

union all

select
    'UNKNOWN' as route_id,
    null as origin,
    null as destination,
    null as transport_mode,
    null as distance_km
