-- Grain: one row per shipment leg (spec 4.1).
--
-- Null product_id/route_id (spec 3.1 injection) are mapped to 'UNKNOWN' dim
-- members, not excluded - see docs/project_spec.md 4.3. A leg with an
-- unknown product also has no safe temp range, so its readings can't be
-- judged in/out of range either; that's the same "kept, not silently
-- defaulted to safe" treatment applied consistently below.
--
-- Drift-flagged readings (int_sensor_readings_drift_flagged.is_drift_flagged)
-- are excluded from minutes_out_of_range/max_temp_deviation_c rather than
-- down-weighted or counted as-is, so a miscalibrated device can't push a leg
-- over/under the risk threshold on bad data. has_drift_affected_readings
-- makes that exclusion visible. If a leg ends up with zero clean readings,
-- spoilage_risk_flag is null ("unscoreable"), not false - no data must not
-- read as confirmed-safe.
with legs_with_shipment as (
    select
        l.leg_id,
        l.shipment_id,
        l.leg_sequence,
        l.device_id,
        l.planned_distance_km,
        l.leg_start_ts,
        l.leg_end_ts,
        l.is_final_leg,
        l.has_cold_chain_break,
        s.ship_date,
        s.carrier_id,
        coalesce(s.product_id, 'UNKNOWN') as product_id,
        coalesce(s.route_id, 'UNKNOWN') as route_id,
        (s.product_id is null or s.route_id is null) as has_missing_metadata
    from {{ ref('stg_shipment_legs') }} l
    inner join {{ ref('stg_shipments') }} s on l.shipment_id = s.shipment_id
),

-- Interval-until-next-reading is computed over ALL readings (before the
-- drift filter) so gaps reflect real elapsed time. A drift-flagged reading's
-- own interval is then simply dropped in leg_reading_stats below, not
-- reassigned to its neighbors - an honest gap in coverage rather than a
-- guess at what a clean sensor would have read.
readings_with_context as (
    select
        r.reading_id,
        r.leg_id,
        r.temperature_value_c,
        r.is_drift_flagged,
        p.safe_temp_min_c,
        p.safe_temp_max_c,
        timestamp_diff(
            coalesce(
                lead(r.reading_ts) over (partition by r.leg_id order by r.reading_ts),
                l.leg_end_ts
            ),
            r.reading_ts,
            minute
        ) as minutes_until_next_reading_or_leg_end
    from {{ ref('int_sensor_readings_drift_flagged') }} r
    inner join legs_with_shipment l on r.leg_id = l.leg_id
    left join {{ ref('dim_product') }} p on l.product_id = p.product_id
),

deviations as (
    select
        *,
        case
            when safe_temp_min_c is null or safe_temp_max_c is null then null
            when temperature_value_c < safe_temp_min_c then safe_temp_min_c - temperature_value_c
            when temperature_value_c > safe_temp_max_c then temperature_value_c - safe_temp_max_c
            else 0
        end as deviation_c
    from readings_with_context
),

leg_reading_stats as (
    select
        leg_id,
        count(*) as total_readings,
        countif(is_drift_flagged) as drift_flagged_readings,
        countif(not is_drift_flagged) as clean_readings,
        sum(
            case
                when not is_drift_flagged and deviation_c > 0
                    then greatest(minutes_until_next_reading_or_leg_end, 0)
                else 0
            end
        ) as minutes_out_of_range,
        max(case when not is_drift_flagged then deviation_c end) as max_temp_deviation_c
    from deviations
    group by leg_id
)

select
    l.leg_id,
    l.shipment_id,
    l.leg_sequence,
    l.device_id,
    l.product_id,
    l.route_id,
    l.carrier_id,
    l.ship_date,
    l.leg_start_ts,
    l.leg_end_ts,
    l.planned_distance_km,
    l.is_final_leg,
    l.has_cold_chain_break,
    l.has_missing_metadata,
    stats.minutes_out_of_range,
    stats.max_temp_deviation_c,
    coalesce(stats.drift_flagged_readings, 0) > 0 as has_drift_affected_readings,
    safe_divide(stats.drift_flagged_readings, stats.total_readings) as pct_readings_drift_flagged,
    case
        when coalesce(stats.clean_readings, 0) = 0 then null
        when stats.minutes_out_of_range > {{ var('spoilage_risk_minutes_threshold') }} then true
        else false
    end as spoilage_risk_flag,
    l.planned_distance_km * c.emissions_factor_kg_co2_per_km as estimated_emissions_kg
from legs_with_shipment l
left join leg_reading_stats stats on l.leg_id = stats.leg_id
left join {{ ref('dim_carrier') }} c on l.carrier_id = c.carrier_id
