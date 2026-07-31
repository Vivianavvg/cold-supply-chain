-- Not in the original spec's model list (see models/silver/README.md "Known
-- gap"), but int_sensor_readings_drift_flagged needs a per-device verdict to
-- attach to each reading, and that verdict has to be computed somewhere.
--
-- Heuristic, not ground truth: a real pipeline has no independent
-- calibration signal to compare against, so this flags devices whose
-- average deviation from their product's safe-range midpoint is both large
-- and persistent across multiple legs. It will miss drifted devices seen on
-- very few legs, and could mistakenly flag a device that happened to serve
-- several legs with genuine cold-chain breaks. Threshold chosen against the
-- generator's injected drift of 2-4C (config.DRIFT_MIN_C/MAX_C) - noise
-- alone (config.py spread) averages out closer to 0 across >=3 legs.
with readings_with_range as (
    select
        r.device_id,
        r.leg_id,
        r.temperature_value_c,
        p.safe_temp_min_c,
        p.safe_temp_max_c
    from {{ ref('int_sensor_readings_normalized') }} r
    inner join {{ ref('stg_shipment_legs') }} l on r.leg_id = l.leg_id
    inner join {{ ref('stg_shipments') }} s on l.shipment_id = s.shipment_id
    inner join {{ ref('stg_product_master') }} p on s.product_id = p.product_id
),

deviations as (
    select
        device_id,
        leg_id,
        temperature_value_c - (safe_temp_min_c + safe_temp_max_c) / 2 as deviation_from_midpoint_c
    from readings_with_range
),

device_stats as (
    select
        device_id,
        count(distinct leg_id) as legs_observed,
        avg(deviation_from_midpoint_c) as avg_deviation_c
    from deviations
    group by device_id
)

select
    device_id,
    legs_observed,
    round(avg_deviation_c, 2) as avg_deviation_c,
    (legs_observed >= 3 and abs(avg_deviation_c) >= 1.5) as is_drift_flagged
from device_stats
