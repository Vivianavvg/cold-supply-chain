-- Removes rapid-fire duplicate readings (spec 3.1): a genuine reading and its
-- near-identical duplicate land 1-10 seconds apart, while legitimate readings
-- from the same device+leg are ~15 minutes apart. A fixed time-bucket dedup
-- would risk splitting a genuine reading pair that straddles a bucket
-- boundary, so this compares each reading to the previous one directly.
with ordered as (
    select
        *,
        lag(reading_ts) over (
            partition by leg_id, device_id order by reading_ts
        ) as prev_reading_ts
    from {{ ref('stg_sensor_readings') }}
)

select
    reading_id,
    leg_id,
    device_id,
    reading_ts,
    ingested_at,
    temperature_value,
    temperature_unit
from ordered
where
    prev_reading_ts is null
    or timestamp_diff(reading_ts, prev_reading_ts, second) > 60
