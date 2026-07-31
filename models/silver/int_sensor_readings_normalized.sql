-- Normalizes mixed C/F readings (spec 3.1) to a single Celsius column.
-- Keeps the original value + unit alongside it so normalization stays
-- auditable rather than overwriting the source reading.
select
    reading_id,
    leg_id,
    device_id,
    reading_ts,
    ingested_at,
    temperature_value,
    temperature_unit,
    case
        when temperature_unit = 'F' then round((temperature_value - 32) * 5 / 9, 2)
        else temperature_value
    end as temperature_value_c
from {{ ref('int_sensor_readings_deduped') }}
