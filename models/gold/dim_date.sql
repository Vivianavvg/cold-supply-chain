-- Spans every date the data actually touches: from the earliest ship_date
-- to the latest leg_end_ts, so no fact row's date can fall outside the dim.
{% set start_date_expr = "(select min(ship_date) from " ~ ref('stg_shipments') ~ ")" %}
{% set end_date_expr = "(select date(max(leg_end_ts)) from " ~ ref('stg_shipment_legs') ~ ")" %}

with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date=start_date_expr,
        end_date="date_add(" ~ end_date_expr ~ ", interval 1 day)"
    ) }}
)

select
    date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day_of_month,
    extract(dayofweek from date_day) as day_of_week,
    format_date('%A', date_day) as day_name,
    format_date('%B', date_day) as month_name,
    extract(dayofweek from date_day) in (1, 7) as is_weekend
from spine
