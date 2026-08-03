-- Spec 6.2: "Drift-flagged sensors excluded from spoilage calculations" -
-- asserts a leg with zero clean (non-drift-flagged) readings gets a null
-- spoilage_risk_flag ("unscoreable"), never true or false. A miscalibrated
-- device's bias must not silently masquerade as a real risk verdict in
-- either direction. See docs/project_spec.md 4.3.
select f.leg_id, f.spoilage_risk_flag
from {{ ref('fct_shipment_conditions') }} f
inner join (
    select leg_id
    from {{ ref('int_sensor_readings_drift_flagged') }}
    group by leg_id
    having countif(not is_drift_flagged) = 0 and count(*) > 0
) all_drifted on f.leg_id = all_drifted.leg_id
where f.spoilage_risk_flag is not null
