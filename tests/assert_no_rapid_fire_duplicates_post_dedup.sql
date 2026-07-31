-- Spec 6.2: "No duplicate timestamps post-dedup" - asserts the dedup logic
-- in int_sensor_readings_deduped actually worked, not just that it ran.
-- A dbt test fails if this query returns any rows, so we select the
-- violations: any two readings from the same device+leg still within 60
-- seconds of each other after dedup.
with ordered as (
    select
        leg_id,
        device_id,
        reading_ts,
        lag(reading_ts) over (
            partition by leg_id, device_id order by reading_ts
        ) as prev_reading_ts
    from {{ ref('int_sensor_readings_deduped') }}
)

select *
from ordered
where
    prev_reading_ts is not null
    and timestamp_diff(reading_ts, prev_reading_ts, second) <= 60
