-- 'UNKNOWN' surrogate member for shipments with a null product_id (spec 3.1
-- injection, ~3% of shipments) - see docs/project_spec.md 4.3 for rationale.
-- fct_shipment_conditions maps null product_id to 'UNKNOWN' rather than
-- excluding the leg.
select
    product_id,
    product_name,
    safe_temp_min_c,
    safe_temp_max_c
from {{ ref('stg_product_master') }}

union all

select
    'UNKNOWN' as product_id,
    'Unknown product' as product_name,
    null as safe_temp_min_c,
    null as safe_temp_max_c
