-- Attaches the device-level drift verdict to every reading. Flagged here,
-- not filtered out - Gold decides whether/how to exclude drift-flagged
-- readings from spoilage_risk_flag (spec 6.2).
select
    r.reading_id,
    r.leg_id,
    r.device_id,
    r.reading_ts,
    r.ingested_at,
    r.temperature_value,
    r.temperature_unit,
    r.temperature_value_c,
    coalesce(d.is_drift_flagged, false) as is_drift_flagged
from {{ ref('int_sensor_readings_normalized') }} as r
left join {{ ref('int_device_drift_flags') }} as d on r.device_id = d.device_id
