select
    event_id,
    shipment_id,
    leg_id,
    event_type,
    event_ts,
    ingested_at
from {{ source('raw', 'shipment_events') }}
