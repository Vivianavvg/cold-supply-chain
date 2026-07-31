-- Spec 6.2: "Out-of-sequence events resolved, not dropped" - row counts
-- before/after sequencing should match, proving events are reordered by
-- true event_ts rather than discarded when their arrival order looks wrong.
with counts as (
    select
        (select count(*) from {{ ref('stg_shipment_events') }}) as source_count,
        (select count(*) from {{ ref('int_shipment_events_sequenced') }}) as sequenced_count
)

select *
from counts
where source_count != sequenced_count
