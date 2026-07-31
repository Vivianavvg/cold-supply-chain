-- Not in the original spec's model list (see data_generator/README.md "Known gap"),
-- but required since the Gold fact grain is one row per shipment leg (spec 4.1).
select
    leg_id,
    shipment_id,
    leg_sequence,
    device_id,
    planned_distance_km,
    leg_start_ts,
    leg_end_ts,
    is_final_leg,
    has_cold_chain_break
from {{ source('raw', 'shipment_legs') }}
