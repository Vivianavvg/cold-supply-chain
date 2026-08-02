-- Spec 6.2: "Every shipment leg has a non-null route and carrier reference" -
-- resolved as: legs from shipments with missing metadata (spec 3.1) are
-- kept, not dropped, and always get a non-null 'UNKNOWN' surrogate key
-- instead (see docs/project_spec.md 4.3). Asserts that resolution actually
-- happened consistently: no raw nulls leaked through to the fact table, and
-- has_missing_metadata agrees exactly with which rows got the 'UNKNOWN'
-- substitution.
select leg_id, product_id, route_id, carrier_id, has_missing_metadata
from {{ ref('fct_shipment_conditions') }}
where
    product_id is null
    or route_id is null
    or carrier_id is null
    or has_missing_metadata != (product_id = 'UNKNOWN' or route_id = 'UNKNOWN')
