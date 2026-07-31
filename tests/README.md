# Singular tests

Custom SQL tests, one file per assertion. Generic tests (unique, not_null, relationships, accepted_values) live in each model's `schema.yml` instead.

Planned (spec §6.2):
- No duplicate timestamps post-dedup
- Drift-flagged sensors excluded from spoilage calculations
- Every shipment leg has a non-null route and carrier reference
- Out-of-sequence events resolved, not dropped (row counts reconcile)
- Unit normalization completeness (no Fahrenheit rows survive Silver)

Not yet implemented — depends on Silver/Gold models existing.
