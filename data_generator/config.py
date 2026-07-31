"""Tunable knobs for synthetic data generation and data-quality injection."""

# Volume
NUM_PRODUCTS = 8
NUM_ROUTES = 15
NUM_CARRIERS = 6
NUM_SHIPMENTS = 500
MIN_LEGS_PER_SHIPMENT = 1
MAX_LEGS_PER_SHIPMENT = 3

# Sensor cadence
READING_INTERVAL_MINUTES = 15

# Data quality injection rates (spec section 3.1)
DROPOUT_RATE = 0.05  # fraction of expected readings silently missing
DUPLICATE_RATE = 0.03  # fraction of readings that get a near-identical duplicate within seconds
DRIFT_DEVICE_RATE = 0.10  # fraction of devices with a persistent calibration offset
DRIFT_MIN_C = 2.0
DRIFT_MAX_C = 4.0
FAHRENHEIT_DEVICE_RATE = 0.25  # fraction of devices reporting in F instead of C
COLD_CHAIN_BREAK_RATE = 0.15  # fraction of legs with a temperature excursion window
OUT_OF_SEQUENCE_RATE = 0.05  # fraction of shipments where the delivered event arrives out of order
MISSING_METADATA_RATE = 0.03  # fraction of shipments with a null product_id or route_id
