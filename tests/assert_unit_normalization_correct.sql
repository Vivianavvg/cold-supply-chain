-- Spec 6.2: "Unit normalization completeness" - asserts every row's
-- temperature_value_c is actually the correct conversion of the original
-- value, not just present. Fails if any row's converted value drifts from
-- the expected formula by more than a small rounding tolerance.
select *
from {{ ref('int_sensor_readings_normalized') }}
where
    (
        temperature_unit = 'F'
        and abs(temperature_value_c - round((temperature_value - 32) * 5 / 9, 2)) > 0.01
    )
    or (
        temperature_unit = 'C'
        and temperature_value_c != temperature_value
    )
