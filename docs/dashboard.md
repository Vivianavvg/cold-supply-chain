# Dashboard (spec §8)

A Looker Studio report connected directly to the `gold` BigQuery dataset, built around one central question (spec §8):

> Which routes/carriers/product categories carry the highest spoilage risk, and what is the emissions cost of choosing a safer (often slower) alternative?

Gold (`fct_shipment_conditions` + `dim_product`/`dim_route`/`dim_carrier`/`dim_date`) is already the presentation-ready layer per spec §5 — no new dbt models were added for this milestone. The 4 views below are plain SQL against Gold, meant to be pasted into Looker Studio as **Custom Query** BigQuery data sources.

All 4 queries were run against the real `cold-chain-supply` project's `gold` dataset before being written down here and returned sensible results (95 route×carrier pairs, 1004 leg-level rows, 16 routes, 181 days).

## The 4 views (spec §8.1)

Replace `<gcp-project-id>` with the real project ID (see `~/.dbt/profiles.yml` — not recorded in this repo, see `docs/session_handoff.md`'s "Environment notes").

### 1. Spoilage risk by route and carrier (heatmap or ranked table)

```sql
select
    r.route_id,
    r.origin,
    r.destination,
    r.transport_mode,
    c.carrier_id,
    c.carrier_name,
    count(*) as total_legs,
    countif(f.spoilage_risk_flag is true) as high_risk_legs,
    countif(f.spoilage_risk_flag is false) as low_risk_legs,
    countif(f.spoilage_risk_flag is null) as unscoreable_legs,
    safe_divide(countif(f.spoilage_risk_flag is true), countif(f.spoilage_risk_flag is not null)) as spoilage_risk_rate
from `<gcp-project-id>.gold.fct_shipment_conditions` f
left join `<gcp-project-id>.gold.dim_route` r on f.route_id = r.route_id
left join `<gcp-project-id>.gold.dim_carrier` c on f.carrier_id = c.carrier_id
group by r.route_id, r.origin, r.destination, r.transport_mode, c.carrier_id, c.carrier_name
```

**Chart:** table or pivot table, rows = route (origin → destination), columns = carrier_name, metric = `spoilage_risk_rate` (format as %) with conditional formatting (heatmap coloring) turned on. `unscoreable_legs` (all-drift-flagged legs, spec §4.3) is broken out separately rather than folded into the risk rate's denominator — a route/carrier pair with a lot of unscoreable legs is itself worth seeing, not hidden.

### 2. Minutes-out-of-range distribution by product category

```sql
select
    p.product_id,
    p.product_name,
    f.leg_id,
    f.minutes_out_of_range
from `<gcp-project-id>.gold.fct_shipment_conditions` f
left join `<gcp-project-id>.gold.dim_product` p on f.product_id = p.product_id
where f.minutes_out_of_range is not null
```

**Chart:** histogram, dimension = `minutes_out_of_range`, breakdown dimension = `product_name`. Left row-level (not pre-aggregated) since Looker Studio's histogram chart buckets from raw rows itself. The `where ... is not null` drops legs with zero clean readings (spec §4.3's "unscoreable" case) — they have no meaningful minutes-out-of-range value, not a zero.

### 3. Emissions vs. spoilage-risk scatter plot per route (the core tradeoff visual)

```sql
select
    r.route_id,
    r.origin,
    r.destination,
    r.transport_mode,
    r.distance_km,
    avg(f.estimated_emissions_kg) as avg_emissions_kg,
    safe_divide(countif(f.spoilage_risk_flag is true), countif(f.spoilage_risk_flag is not null)) as spoilage_risk_rate,
    count(*) as total_legs
from `<gcp-project-id>.gold.fct_shipment_conditions` f
left join `<gcp-project-id>.gold.dim_route` r on f.route_id = r.route_id
group by r.route_id, r.origin, r.destination, r.transport_mode, r.distance_km
```

**Chart:** scatter, X = `avg_emissions_kg`, Y = `spoilage_risk_rate`, dimension (point label/color) = `transport_mode`, optional bubble size = `total_legs`. This is the one chart that directly answers the spec's central question — routes in the bottom-right (low risk, low emissions) are the ones worth calling out; routes in the top-left are the explicit tradeoff (slower/safer but more emissions-heavy alternative exists, or vice versa).

### 4. Spoilage risk trend over time

```sql
select
    d.date_day,
    d.year,
    d.month,
    d.month_name,
    count(*) as total_legs,
    countif(f.spoilage_risk_flag is true) as high_risk_legs,
    safe_divide(countif(f.spoilage_risk_flag is true), countif(f.spoilage_risk_flag is not null)) as spoilage_risk_rate
from `<gcp-project-id>.gold.fct_shipment_conditions` f
left join `<gcp-project-id>.gold.dim_date` d on date(f.leg_start_ts) = d.date_day
group by d.date_day, d.year, d.month, d.month_name
order by d.date_day
```

**Chart:** time series, dimension = `date_day`, metric = `spoilage_risk_rate` (or `high_risk_legs` for absolute counts). Trended on `leg_start_ts` (when a leg's transit actually happened), not the shipment-level `ship_date` — a multi-leg shipment's later legs can start days after `ship_date`, so trending on `ship_date` would misdate that risk.

**Known limitation:** spec §7.2 (the optional daily scheduled production run that would regenerate raw data and re-run the pipeline daily) was **not implemented** (see `docs/session_handoff.md`) — so this trend reflects one static `--seed 42` snapshot (Feb–Aug 2026 in the generated data), not a live-growing time series. It'll still demonstrate the intended shape of the chart; it just won't gain new days on its own without manually regenerating data, reloading, and rebuilding.

## Looker Studio setup (manual — needs your Google login)

1. Go to [lookerstudio.google.com](https://lookerstudio.google.com) signed in with the Google account that owns/has access to the `cold-chain-supply` GCP project (should already work if you're the project owner — no extra IAM setup needed; Looker Studio uses your own Google identity's BigQuery permissions, not the service account key).
2. **Create → Report**.
3. **Add data → BigQuery → Custom Query** (not "My Projects" table browsing, since these are joins/aggregations, not single tables). Select the `cold-chain-supply` project (billing project), paste **query 1** above, click **Add**.
4. Build the table/pivot chart for view 1 as described above.
5. Repeat **Add data → BigQuery → Custom Query** for each of the other 3 queries — Looker Studio treats each Custom Query as its own data source, so this report ends up with 4 data sources, one per chart, rather than one shared source with blending.
6. Arrange the 4 charts on the report canvas (e.g., a 2×2 grid), add a report title, and set percentage-format fields (`spoilage_risk_rate`) to show as `%` in each chart's Style panel.
7. Share/publish the report per your usual Looker Studio sharing settings — that part isn't something this repo or Claude Code can decide for you (this is where the "portfolio project" gets a viewable link).
