-- Not in the original spec's model list (see data_generator/README.md "Known gap"),
-- but required as the upstream source for shipment-level product/route/carrier refs.
select
    shipment_id,
    product_id,
    route_id,
    carrier_id,
    ship_date
from {{ source('raw', 'shipments') }}
