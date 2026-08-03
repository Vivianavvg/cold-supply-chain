# Cold-Chain Visibility & Spoilage Risk Analytics

An Analytics Engineering Project using dbt, BigQuery, and the Medallion Architecture

Draft v0.1 — transcribed from `coldchain_project_spec.docx`. Several tables in the original doc are header-only (no rows filled in); those are marked `TBD` below rather than invented.

## 0. Project Overview

This project builds a production-style analytics pipeline that turns raw, noisy cold-chain sensor and shipment data into a reliable, tested star schema for tracking spoilage risk and estimated carbon cost at the shipment-leg level.

It follows the same technical pattern as a standard fleet-GPS analytics engineering project — dbt, BigQuery, Medallion Architecture (Bronze/Silver/Gold), automated testing, and CI/CD — but applies it to a domain with a sharper business story: which shipments are at risk of spoiling, and what is the tradeoff between a faster/higher-emission route and a slower/safer one?

### 0.1 Why this domain, not generic fleet GPS

- Fleet GPS tracking is the most common version of this portfolio project; cold-chain adds a distinct business payoff (reduced waste + reduced emissions) rather than just "where is the truck."
- The data quality problems are more varied and interesting: unit mismatches (°C vs °F across vendors), calibration drift, and safe-range logic that depends on product type — not just GPS noise.
- It ties directly to a real supply chain pain point: spoilage is both a financial loss and a sustainability problem, giving the final dashboard a genuine "so what."

### 0.2 What "done" looks like

A GitHub repository containing: a data generator, a dbt project with Bronze/Silver/Gold models, a documented star schema, a test suite (~15-20 tests), a working CI/CD pipeline, and a simple dashboard answering the spoilage-vs-emissions question. Someone unfamiliar with the project should be able to clone the repo, run it, and understand the data model from documentation alone.

## 1. Objectives

- Simulate realistic, imperfect cold-chain sensor and shipment data with deliberately injected data quality issues.
- Design and implement a Medallion Architecture (Bronze → Silver → Gold) in dbt that resolves those issues transparently and auditably.
- Produce a documented star schema answering a real business question about spoilage risk and route/carrier performance.
- Build an automated test suite that catches data quality regressions before they reach the Gold layer.
- Stand up a CI/CD pipeline so every change is validated automatically, mirroring how this would run in a real organization.
- Present the results in a lightweight dashboard that makes the spoilage-risk / emissions tradeoff visible at a glance.

## 2. Architecture Overview

The pipeline follows the Medallion Architecture: each layer has a distinct responsibility, and data only moves forward, never backward.

| Layer | Responsibility | Key operations |
|---|---|---|
| Bronze | TBD | TBD |
| Silver | TBD | TBD |
| Gold | TBD | TBD |

(Narrative detail for each layer's responsibilities lives in §5 and in each `models/<layer>/README.md`.)

### 2.1 Tech stack

- **Warehouse:** Google BigQuery (free-tier sandbox suitable for this data volume).
- **Transformation:** dbt Core, version-controlled in the same repo as the rest of the project.
- **Data generation:** Python script(s) producing synthetic sensor and shipment data with configurable noise/error injection.
- **Orchestration/CI:** GitHub Actions for test runs on pull requests; optional scheduled job to simulate a production cadence.
- **Presentation:** Looker Studio (or an equivalent lightweight BI tool) connected directly to Gold tables.

## 3. Data Sources (Simulated)

Real cold-chain sensor data is not publicly available at usable scale, so this project deliberately simulates it — which is a feature, not a limitation, because it allows every data quality problem in the pipeline to be intentional and provable.

| Source | Description | Approx. grain |
|---|---|---|
| TBD | TBD | TBD |

### 3.1 Injected data quality problems

Built into the generator on purpose, so the pipeline's ability to catch and resolve them can be demonstrated and tested:

- **Sensor dropout** — gaps in the reading stream (simulating lost signal in transit).
- **Duplicate rapid-fire readings** — multiple near-identical timestamps from the same device within seconds.
- **Calibration drift** — a subset of devices consistently reporting 2–4 degrees off from ground truth.
- **Unit inconsistency** — some simulated device vendors report Fahrenheit, others Celsius.
- **Out-of-sequence events** — a "delivered" event occasionally landing in the stream before some in-transit readings, simulating network lag between systems.
- **Missing/null product or route references** — a small percentage of shipments with incomplete metadata, to test referential integrity handling.

## 4. Data Model

### 4.1 Grain decision

The Gold fact table grain is one row per shipment leg (the segment of a shipment between two consecutive checkpoints), not one row per sensor reading. This is a deliberate design decision: sensor-level detail belongs in Silver; the fact table answers a business question at a grain a decision-maker actually cares about.

### 4.2 Star schema

| Table | Type | Key columns |
|---|---|---|
| `fct_shipment_conditions` | Fact, one row per shipment leg | `leg_id` (PK), `shipment_id`, `product_id`/`route_id`/`carrier_id` (FKs), `ship_date` (FK to `dim_date`) |
| `dim_product` | Dimension + `'UNKNOWN'` surrogate member | `product_id` (PK) |
| `dim_route` | Dimension + `'UNKNOWN'` surrogate member | `route_id` (PK) |
| `dim_carrier` | Dimension, no `'UNKNOWN'` member (`carrier_id` never null in source) | `carrier_id` (PK) |
| `dim_date` | Date spine, min `ship_date` to max `leg_end_ts` | `date_day` (PK) |

Implemented in `models/gold/`.

### 4.3 Key derived metrics (computed in Gold)

- `minutes_out_of_range` — total minutes a shipment leg spent outside the product's safe temperature range. Computed only from readings where `is_drift_flagged = false` (see decision below).
- `max_temp_deviation_c` — the single worst deviation from the safe range during the leg, same drift exclusion as above.
- `spoilage_risk_flag` — boolean/tiered flag based on configurable thresholds (e.g., >30 minutes out of range = high risk). **Decided:** readings from drift-flagged devices (`int_sensor_readings_drift_flagged.is_drift_flagged`) are excluded from the `minutes_out_of_range` calc entirely, rather than down-weighted or counted as-is — a biased device could otherwise push a leg over/under the risk threshold on bad data. The fact table also carries `has_drift_affected_readings` (or `pct_readings_drift_flagged`) so this exclusion is visible, not silent. If a leg has zero clean (non-drift-flagged) readings, `spoilage_risk_flag` is `NULL`/`'unscoreable'`, not `false` — "no valid data" must not read as "confirmed safe."
- `estimated_emissions_kg` — estimated carbon emissions for the leg. **Decided:** `planned_distance_km * carriers.emissions_factor_kg_co2_per_km`. Deliberately excludes a `transport_mode` multiplier: the generator ties `transport_mode` to leg speed/duration, not to any emissions factor, so a mode multiplier would be an invented number rather than one derived from the data as generated.

**Decided — null `product_id`/`route_id` handling:** shipments with a null `product_id` or `route_id` (§3.1 injection, ~3% of shipments) are **kept** in `fct_shipment_conditions`, not excluded, using an `'UNKNOWN'` surrogate member in `dim_product`/`dim_route` (standard Kimball pattern). A `has_missing_metadata` flag on the fact row makes this visible. Rationale: excluding these legs would silently under-report shipment volume and — more importantly — a null `product_id` means the safe temperature range is unknown, so spoilage risk can't be assessed for that leg either; dropping it would make the exact shipments most worth flagging invisible instead. Same principle as the drift-flagged decision above: missing/untrustworthy data must be visible and marked unscoreable, never silently dropped or defaulted into a false "safe" result.

## 5. dbt Project Structure

A conventional dbt layout, with model folders matching the Medallion layers:

```
models/
  bronze/
    stg_sensor_readings.sql
    stg_shipment_events.sql
    stg_route_metadata.sql
    stg_product_master.sql
    stg_carrier_master.sql
  silver/
    int_sensor_readings_deduped.sql
    int_sensor_readings_normalized.sql
    int_sensor_readings_drift_flagged.sql
    int_shipment_events_sequenced.sql
  gold/
    fct_shipment_conditions.sql
    dim_product.sql
    dim_route.sql
    dim_carrier.sql
    dim_date.sql
tests/
  (singular tests — see §6)
seeds/
  (small static reference data if needed)
```

## 6. Testing Plan

Target: roughly 15–20 tests across generic and custom categories. This is what distinguishes a "production-grade" pipeline from a notebook exercise — every data quality assumption in §3.1 should have a corresponding test that would fail if that problem leaked into Gold.

### 6.1 Generic dbt tests

| Test type | Applied to | Purpose |
|---|---|---|
| TBD | TBD | TBD |

### 6.2 Custom / singular tests

- **No duplicate timestamps post-dedup** — asserts the Silver deduplication logic actually worked, not just that it ran.
- **Drift-flagged sensors excluded from spoilage calculations** — asserts a device known to be miscalibrated doesn't silently produce a false `spoilage_risk_flag`.
- **Every shipment leg has a non-null route and carrier reference** — catches metadata gaps described in §3.1 before they reach Gold.
- **Out-of-sequence events resolved, not dropped** — row counts before/after sequencing logic should match (minus documented exclusions), proving events are being reordered, not discarded.
- **Unit normalization completeness** — asserts no row in Silver still reports Fahrenheit after the normalization step.

### 6.3 Test documentation

Each test's purpose should be documented directly in `schema.yml` descriptions, so the test suite itself doubles as living documentation of the data quality rules the project enforces.

## 7. CI/CD Pipeline

### 7.1 Pull request workflow

- A pull request against `main` triggers a GitHub Actions workflow.
- The workflow spins up a dbt run against a BigQuery dev/sandbox dataset (isolated from production).
- `dbt build` runs (models + tests together); the workflow fails if any test fails.
- Merge to `main` is blocked until the workflow passes.

### 7.2 Optional: scheduled production run

A separate scheduled GitHub Actions workflow (e.g., daily) simulates a production cadence: generates a new batch of raw data, runs the full Bronze → Silver → Gold pipeline against the production dataset, and posts a summary (row counts, test pass/fail, any new spoilage-risk flags) — this is what elevates the project from "I can run dbt" to "I built something that could run unattended."

### 7.3 CI/CD architecture sketch

```
PR opened  ─▶  GitHub Actions  ─▶  dbt build (dev dataset)  ─▶  tests pass? ─▶ merge allowed
Daily cron ─▶  generate new raw data ─▶  dbt build (prod dataset) ─▶  summary posted
```

## 8. Presentation Layer

A lightweight dashboard (Looker Studio or equivalent) connected directly to the Gold star schema, built around one central question:

> "Which routes/carriers/product categories carry the highest spoilage risk, and what is the emissions cost of choosing a safer (often slower) alternative?"

### 8.1 Suggested views

- Spoilage risk by route and carrier (heatmap or ranked table).
- Minutes-out-of-range distribution by product category.
- Emissions vs. spoilage-risk scatter plot per route — the core "tradeoff" visual.
- A trend view showing spoilage risk over time, useful for demonstrating the daily/scheduled pipeline in action.

## 9. Milestones & Suggested Timeline

| Milestone | Deliverable | Approx. duration |
|---|---|---|
| TBD | TBD | TBD |

Total: roughly 3–4 weeks at a steady, part-time pace. Milestones are sequential but M2 (data generator) can be revisited iteratively as data quality edge cases are discovered while building Silver models.

## 10. Success Criteria

- Pipeline runs end-to-end from raw simulated data to Gold tables without manual intervention.
- All ~15–20 tests pass on a clean run, and can be shown to fail when a data quality issue is deliberately reintroduced (a good demo moment).
- CI/CD blocks a pull request that breaks a test — demonstrated with at least one intentional "bad" PR.
- The dashboard answers the spoilage-vs-emissions question clearly enough that someone unfamiliar with the project understands the tradeoff within a minute of looking at it.
- README documentation is complete enough that a stranger could clone the repo and run the whole pipeline themselves.

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| TBD | TBD |

## 12. Stretch Goals (Optional, Post-MVP)

- Add a second carrier data format (different column names/units) to simulate the real multi-vendor reconciliation problem, testing the pipeline's robustness to schema drift.
- Add anomaly detection (simple statistical, not ML) to flag sensors trending toward failure before they fully drift out of range.
- Add a cost dimension (estimated dollar value of spoiled goods per shipment) to pair the emissions tradeoff with a financial one.
- Containerize the whole pipeline (Docker) so it can be handed to someone else to run with a single command.
