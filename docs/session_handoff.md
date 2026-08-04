# Session handoff

Working notes so a new session can pick this project up without re-deriving context. Update this file at the end of each work session rather than trusting memory across sessions.

## Project

Cold-Chain Visibility & Spoilage Risk Analytics — dbt/BigQuery portfolio project. Full spec: `docs/project_spec.md` (transcribed from the original `.docx`; some spec tables were header-only in the source doc and are marked `TBD`).

Repo: https://github.com/Vivianavvg/cold-supply-chain (owner: Vivianavvg)

## Workflow being followed

Feature branch → push → open PR on github.com → user merges via the web UI → pull `main` locally → delete the merged local branch → branch again for the next milestone. `gh` CLI is **not installed** on this machine, so PRs must be opened/merged manually on github.com; Claude can push branches and give the PR URL but cannot merge.

`.github/workflows/ci.yml` will show **all checks failed** on every PR — this is expected and fine to ignore/merge through. It's a placeholder from the initial scaffold that references a BigQuery service account and `profiles.yml` `ci` target that don't exist yet. Real CI/CD is its own milestone (spec §7), planned after Gold.

## Status as of this handoff

| Milestone | Branch | State |
|---|---|---|
| Repo scaffold | `main` | Merged |
| M2: Data generator | `main` (was `feature/data-generator`) | Merged |
| Bronze staging models | `main` (was `feature/bronze-models`) | Merged |
| Silver intermediate models + 3 tests | `main` (was `feature/silver-models`) | Merged (PR #3) |
| Gold star schema | `main` (was `feature/gold-models`) | Merged (PR #4) |
| BigQuery sandbox + first real `dbt build` | `feature/bigquery-setup` | **Done — `dbt build` green, PR open** |
| CI/CD (real) | — | Not started |
| Dashboard | — | Not started |

**Next action when resuming:** merge the `feature/bigquery-setup` PR (see below), pull `main`, delete the local branch, then start either CI/CD (spec §7) or the dashboard (spec §8) — both are open, pick either.

**Note on this handoff doc's history:** this file's original commit (`fc1ba2f`) was made *after* PR #3 had already been merged, so it never made it into `main` via that PR — it sat orphaned on `feature/silver-models` until cherry-picked directly onto `main` in a later session. If a future PR merge seems to "lose" doc-only commits made close to merge time, check for the same race — commits pushed after a PR merges don't ride along.

## What exists and why (decisions made along the way)

- **`data_generator/`** (Python, `generate.py` + `config.py`) — produces 7 raw CSVs (products, carriers, routes, shipments, shipment_legs, sensor_readings, shipment_events) into `data_generator/output/` (gitignored, regenerate with `python generate.py --seed 42`). Injects all 6 data quality problems from spec §3.1 and writes a `data_quality_summary.txt` with exact injected counts per run, so downstream tests can be checked against known-true numbers.
- **Known gap vs. spec §5**: the spec's Bronze model list names 5 staging models but none for shipment/leg identity. Added `stg_shipments` and `stg_shipment_legs` beyond the spec's list — necessary because the Gold grain (one row per shipment leg, spec §4.1) needs an upstream source for it. Documented in `data_generator/README.md` and `models/bronze/README.md`.
- **`models/bronze/`** — 7 staging models (5 spec-named + the 2 above), light rename/type-cast only. Sources declared in `_bronze__sources.yml` against a `raw` BigQuery dataset (doesn't exist yet). Generic tests (unique/not_null/accepted_values/relationships) in `_bronze__models.yml`. `stg_shipments.product_id`/`route_id` are deliberately **not** `not_null`-tested — nulls there are the intentional spec §3.1 injection, not a bug.
- **`models/silver/`** — dedup (`int_sensor_readings_deduped`, LAG-based comparison rather than fixed time-bucket rounding, to avoid splitting a genuine reading pair that straddles a bucket boundary), unit normalization (`int_sensor_readings_normalized`, keeps original value+unit for audit), calibration-drift flagging (`int_device_drift_flags` + `int_sensor_readings_drift_flagged`), event sequencing (`int_shipment_events_sequenced`, orders by true `event_ts` not arrival order).
  - `int_device_drift_flags` is **not in the spec's model list** — added because the drift-flagged model needs a per-device verdict from somewhere. It's a **statistical heuristic, not ground truth**: flags a device if its average deviation from the product's safe-range midpoint is ≥1.5°C across ≥3 legs. Real pipelines don't have ground truth for this either. Verified against real generator output (via DuckDB, since no BigQuery project exists to run actual `dbt`): 22/199 devices flagged vs. ~20 true drifted devices — reasonable but not exact.
- **No BigQuery project, no `profiles.yml` exist yet** — nothing in `models/` has actually been run through `dbt`. All SQL has instead been sanity-checked by hand-translating the logic into DuckDB against real generator output (dedup count matched the exact injected duplicate count, zero normalization violations, exact row-count parity on event sequencing). This should still happen for real once a BigQuery sandbox is set up — don't assume DuckDB verification is equivalent to `dbt build` passing.
- **Tests**: 3 of the spec's 5 singular tests (§6.2) are written — dedup effectiveness, normalization correctness, event row-count parity. The other 2 (drift-exclusion from spoilage calc, non-null route/carrier per leg) need Gold to exist first; noted in `tests/README.md`.

## Gold (implemented on `feature/gold-models`, 2026-08-01)

- **`models/gold/dim_product.sql`, `dim_route.sql`** — real rows + an `'UNKNOWN'` surrogate member. **Decided:** null `product_id`/`route_id` (spec §3.1 injection, ~3% of shipments) are kept in `fct_shipment_conditions`, not excluded, coalesced to `'UNKNOWN'`, with `has_missing_metadata` flagging it. Rationale: excluding would silently under-report shipment volume, and since `product_id` determines the safe temp range, dropping these legs would make exactly the shipments most worth checking invisible instead of flagged. Full writeup in `docs/project_spec.md` §4.3.
- **`models/gold/dim_carrier.sql`** — real rows only, no `'UNKNOWN'` member (`carrier_id` is never null in the generator).
- **`models/gold/dim_date.sql`** — `dbt_utils.date_spine` from earliest `ship_date` to latest `leg_end_ts`. Untested against BigQuery (see below) — `dbt_utils` behavior with subquery start/end bounds specifically hasn't been run for real, only reasoned through.
- **`models/gold/fct_shipment_conditions.sql`** — one row per shipment leg. **Decided:** readings where `is_drift_flagged = true` are excluded entirely from `minutes_out_of_range`/`max_temp_deviation_c` (not down-weighted, not counted as-is) — a biased device could otherwise push a leg over/under the risk threshold on bad data. `has_drift_affected_readings`/`pct_readings_drift_flagged` make the exclusion visible. If a leg has zero clean readings after exclusion, `spoilage_risk_flag` is `NULL` ("unscoreable"), not `false`. Same "visible, never silently defaulted to safe" principle as the null-metadata decision. `estimated_emissions_kg = planned_distance_km * carriers.emissions_factor_kg_co2_per_km` — **decided** not to invent a `transport_mode` multiplier, since the generator doesn't tie one to emissions (only to leg speed/duration). `spoilage_risk_minutes_threshold` (default 30, spec's example) is a dbt var in `dbt_project.yml`, not hardcoded. Full writeup in `docs/project_spec.md` §4.3.
- **`has_cold_chain_break`** flows through from `stg_shipment_legs` into the fact table — it's generator ground truth (`config.COLD_CHAIN_BREAK_RATE`), not something a real pipeline would have, kept only so `spoilage_risk_flag` can eventually be validated against a known-true answer (same role `int_device_drift_flags`' verification played for drift).
- **Tests**: both deferred singular tests from §6.2 are now written against real Gold SQL — `tests/assert_drift_flagged_legs_unscoreable.sql`, `tests/assert_missing_metadata_resolved_consistently.sql`. All 5 of the spec's singular tests now exist.
- **DuckDB verification** (same caveat as Bronze/Silver — no BigQuery project yet, so nothing has run through real `dbt`): against `--seed 42` output (1004 shipment legs) — fact row count matches leg count exactly (1004=1004), zero null FKs, zero `has_missing_metadata` mismatches, zero negative `minutes_out_of_range`, zero violations of the "all-drift-flagged legs get `NULL` spoilage_risk_flag" invariant, dim row counts match source+1 (product/route) or source (carrier) exactly. `spoilage_risk_flag` came out 812 false / 71 true / 121 null across the 1004 legs; cross-tabbed against the `has_cold_chain_break` ground truth, 53/79 (~67%) of truly-broken legs were caught as high-risk where scoreable — reasonable given the heuristic drift-exclusion and 30-minute threshold, not exact (same "reasonable but not exact" caveat as the drift-flag heuristic itself). `dbt_utils.date_spine`'s subquery-bounds usage in `dim_date` was **not** DuckDB-verified (DuckDB's date functions differ enough from BigQuery's that hand-translating it wasn't worthwhile) — double check this one first when a real BigQuery sandbox exists.

## BigQuery sandbox setup (started 2026-08-03, finished 2026-08-04)

Goal: get `dbt build` running for real for the first time (spec §2.1: Google Cloud, free tier). Chosen approach: service account key file auth (not `gcloud` CLI/OAuth — `gcloud` isn't installed on this machine and we deliberately didn't install it).

**Done:**
- GCP project created: **project ID `<gcp-project-id>`** (see local `~/.dbt/profiles.yml` for the real value — not recorded here since this repo may go public). Billing linked (required — BigQuery "Sandbox" mode with no billing account blocks service account creation entirely, so this couldn't be avoided for the key-file approach).
- Service account created: `dbt-coldchain` → email `<service-account-email>` (see local `~/.dbt/profiles.yml` / GCP console — not recorded here), roles **BigQuery Data Editor** + **BigQuery Job User**.
- JSON key downloaded and moved (not copied) from `~/Downloads/` to **`C:\Users\Vacav\.dbt\keys\<gcp-project-id>-sa.json`** — outside the repo, never committed, confirmed no longer present in Downloads. This file is a live credential; treat it like a password, don't paste its contents anywhere, don't move it back into a synced/repo folder.
- `pip install dbt-core dbt-bigquery google-cloud-bigquery` — installed. Versions: dbt-core 1.12.0, dbt-bigquery 1.12.0, google-cloud-bigquery 3.42.3.
  - **Gotcha specific to this machine**: `python3` resolves to the Windows Store Python, which installs console scripts to a sandboxed path, NOT a normal `Scripts` dir on PATH. `python3 -m dbt` does **not** work (`No module named dbt.__main__`). The real `dbt.exe` is at:
    `C:/Users/Vacav/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/Scripts/dbt.exe`
    Call it directly by that path (or add that Scripts dir to PATH) rather than `python3 -m dbt` or a bare `dbt`.
- `~/.dbt/profiles.yml` written (outside repo, standard dbt location):
  ```yaml
  coldchain_analytics:
    target: dev
    outputs:
      dev:
        type: bigquery
        method: service-account
        project: <gcp-project-id>
        dataset: dbt_default
        threads: 4
        keyfile: C:/Users/Vacav/.dbt/keys/<gcp-project-id>-sa.json
        location: US
  ```
- `macros/generate_schema_name.sql` added (**uncommitted**, sitting on `main` — see branch note above) — overrides dbt's default schema-prefixing so `+schema: bronze/silver/gold` in `dbt_project.yml` produce literal dataset names `bronze`/`silver`/`gold` instead of `dbt_default_bronze` etc. Standard, documented dbt-labs override pattern.
- `dbt.exe --version` confirmed working end-to-end (core + bigquery plugin both report 1.12.0).

**Remaining steps — all done 2026-08-04:**
1. `dbt deps` — done (dbt_utils 1.4.1 installed, `dbt_packages/` + `package-lock.yml` present). This had actually already completed silently in a prior interrupted session; confirmed rather than re-run.
2. `dbt debug` — passes clean (`All checks passed!`). Note: `logs/dbt.log` has a stale entry showing a *different* `dbt debug` invocation from the same prior session hanging for ~15 hours before finally erroring with a connection timeout/reset — looked alarming at first glance but was leftover process noise, not a real problem; a fresh `dbt debug` run this session connected in ~11s with no issue. If a future session sees a huge elapsed-time gap in `dbt.log`, check whether it's just an old hung invocation before assuming the credentials are broken.
3. `raw` dataset created and all 7 CSVs loaded via a new script, **`data_generator/load_to_bigquery.py`** (uses `google.cloud.bigquery` `LoadJobConfig` with `autodetect=True` so columns land as real `TIMESTAMP`/`DATE`/`FLOAT`/`BOOLEAN` types, not all `STRING` — the bronze staging models select raw columns with no casting, so this matters). Run manually, not part of the dbt DAG: `GCP_PROJECT=<gcp-project-id> GOOGLE_APPLICATION_CREDENTIALS=<keyfile path> python3 data_generator/load_to_bigquery.py` (script reads the project ID from `GCP_PROJECT` rather than hardcoding it, since this file is committed). Row counts loaded matched the generator's `--seed 42` output exactly (500 shipments, 1004 shipment_legs, 82327 sensor_readings, 1504 shipment_events, plus the 3 small dim-ish tables).
4. `dbt build` — **passed completely on the first real run**: 86/86 nodes green (17 models + 69 tests), 0 errors, 0 warnings except one cosmetic deprecation notice (see below). `dim_date`'s `dbt_utils.date_spine` call — the one piece explicitly flagged as unverified by DuckDB — worked with no changes needed. No SQL had to be fixed at all; the from-documentation BigQuery dialect functions (`timestamp_diff`, `countif`, `safe_divide`, `format_date`, `extract(dayofweek ...)`) were all correct on the first try. Cross-checked `fct_shipment_conditions.spoilage_risk_flag` distribution against the earlier DuckDB numbers: **exact match**, 812 false / 71 true / 121 null across 1004 legs.
   - **Deprecation notice** (not an error, build still passed): dbt 1.12 flags the `accepted_values`/other generic test configs in `_bronze__models.yml` that pass args top-level (e.g. `tests: [accepted_values: {values: [...]}]`) instead of nested under an `arguments:` key — `MissingArgumentsPropertyInGenericTestDeprecation`, 15 occurrences. Cosmetic today; will need nesting under `arguments:` before whatever future dbt version turns this into a hard error. Not fixed in this session — small, unrelated to the sandbox milestone, left as a follow-up.
5. Committed `macros/generate_schema_name.sql` + `data_generator/load_to_bigquery.py` on `feature/bigquery-setup`, pushed, PR opened.

## Still open

- Merge the `feature/bigquery-setup` PR (link above/in PR history).
- Minor: nest the `accepted_values` test args under `arguments:` in `_bronze__models.yml` to clear the dbt 1.12 deprecation warning (see above) — small, no rush.
- Minor: `requirements.txt` currently pins `dbt-bigquery~=1.8` but the sandbox actually runs on `dbt-core`/`dbt-bigquery` 1.12.0 (installed outside `requirements.txt`, per the note below) — worth reconciling next time dependencies are touched.
- CI/CD (spec §7) and the dashboard (spec §8) are the next real milestones now that all three model layers are verified against a live warehouse.

## Environment notes

- No `gh` CLI on this machine (checked both Bash and PowerShell) — PRs are manual via github.com.
- No `gcloud`/`bq` CLI on this machine either — deliberately not installed; BigQuery auth goes through a service account key file instead (see "BigQuery sandbox setup" above), and CSV loading goes through the `google-cloud-bigquery` Python client rather than `bq load`.
- `pandas`, `Faker`, `duckdb`, `dbt-core`, `dbt-bigquery`, `google-cloud-bigquery` are installed in whatever Python `python3` resolves to on this machine (Windows Store Python). `duckdb` isn't in `requirements.txt` — it's a local verification tool only, not a project dependency; the three dbt/BigQuery packages aren't in `requirements.txt` either yet (that file has historically been for the data generator's deps only — worth deciding whether to add a `requirements-dbt.txt` or similar once the sandbox setup is finished).
- **Windows Store Python gotcha**: `python3 -m dbt` doesn't work — see the `dbt.exe` full path note in "BigQuery sandbox setup" above.
