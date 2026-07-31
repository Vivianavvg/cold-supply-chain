select
    product_id,
    product_name,
    safe_temp_min_c,
    safe_temp_max_c
from {{ source('raw', 'products') }}
