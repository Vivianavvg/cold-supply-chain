select
    route_id,
    origin,
    destination,
    transport_mode,
    distance_km
from {{ source('raw', 'routes') }}
