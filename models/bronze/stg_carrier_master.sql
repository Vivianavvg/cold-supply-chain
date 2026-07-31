select
    carrier_id,
    carrier_name,
    fuel_type,
    emissions_factor_kg_co2_per_km
from {{ source('raw', 'carriers') }}
