select
    reading_id,
    leg_id,
    device_id,
    reading_ts,
    ingested_at,
    temperature_value,
    temperature_unit
from {{ source('raw', 'sensor_readings') }}
