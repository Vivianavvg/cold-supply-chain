-- Orders events by when they actually happened (event_ts), not when they
-- arrived (ingested_at) - the delivered event occasionally arrives out of
-- order (spec 3.1). No rows are dropped, only reordered; see the singular
-- test asserting row-count parity with stg_shipment_events.
select
    event_id,
    shipment_id,
    leg_id,
    event_type,
    event_ts,
    ingested_at,
    row_number() over (partition by shipment_id order by event_ts) as event_sequence
from {{ ref('stg_shipment_events') }}
