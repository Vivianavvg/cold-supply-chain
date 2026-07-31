"""Synthetic cold-chain data generator.

Produces raw CSVs simulating cold-chain shipment tracking, with the data
quality problems from project spec section 3.1 deliberately injected:
sensor dropout, duplicate rapid-fire readings, calibration drift, unit
inconsistency (C/F), out-of-sequence events, and missing product/route
references. Injection counts are tracked during generation and written to
a summary file so downstream tests can be written against known-true
numbers rather than re-deriving them from the output.

Note: the project spec's bronze model list (section 5) does not name a
staging model for shipment/leg identity — this generator produces
`shipments.csv` and `shipment_legs.csv` as the necessary upstream sources
for the shipment-leg grain (spec section 4.1). When building Bronze,
either add `stg_shipments`/`stg_shipment_legs` models or fold this into
an existing one.
"""

import argparse
import random
from datetime import timedelta, datetime, date

import pandas as pd
from faker import Faker

import config as cfg

fake = Faker()

PRODUCT_CATALOG = [
    ("Fresh Produce", 2.0, 8.0),
    ("Dairy", 2.0, 6.0),
    ("Frozen Seafood", -22.0, -18.0),
    ("Chilled Meat", 0.0, 4.0),
    ("Cut Flowers", 4.0, 10.0),
    ("Vaccines", 2.0, 8.0),
    ("Ice Cream", -22.0, -18.0),
    ("Pharmaceuticals", 2.0, 8.0),
]

FUEL_TYPES = [
    ("diesel", 0.90),
    ("biodiesel", 0.55),
    ("electric", 0.05),
    ("jet_fuel", 1.85),
    ("marine_diesel", 0.015),
]

TRANSPORT_MODES = ["truck", "rail", "air", "sea"]
SPEED_KMH = {"truck": 70, "rail": 90, "air": 700, "sea": 35}

DEVICE_POOL_SIZE = 200


def generate_products(n):
    rows = []
    for i, (name, lo, hi) in enumerate(PRODUCT_CATALOG[:n], start=1):
        rows.append(
            {
                "product_id": f"PROD-{i:03d}",
                "product_name": name,
                "safe_temp_min_c": lo,
                "safe_temp_max_c": hi,
            }
        )
    return pd.DataFrame(rows)


def generate_carriers(n):
    rows = []
    for i in range(1, n + 1):
        fuel_type, factor = random.choice(FUEL_TYPES)
        rows.append(
            {
                "carrier_id": f"CARR-{i:03d}",
                "carrier_name": fake.company(),
                "fuel_type": fuel_type,
                "emissions_factor_kg_co2_per_km": factor,
            }
        )
    return pd.DataFrame(rows)


def generate_routes(n):
    rows = []
    for i in range(1, n + 1):
        mode = random.choice(TRANSPORT_MODES)
        distance = {
            "truck": random.uniform(50, 1200),
            "rail": random.uniform(200, 2500),
            "air": random.uniform(500, 9000),
            "sea": random.uniform(1000, 15000),
        }[mode]
        rows.append(
            {
                "route_id": f"ROUTE-{i:03d}",
                "origin": fake.city(),
                "destination": fake.city(),
                "transport_mode": mode,
                "distance_km": round(distance, 1),
            }
        )
    return pd.DataFrame(rows)


def build_device_profiles(pool_size):
    """Persistent per-device attributes: unit reported, calibration drift."""
    profiles = {}
    for i in range(1, pool_size + 1):
        device_id = f"DEV-{i:04d}"
        uses_fahrenheit = random.random() < cfg.FAHRENHEIT_DEVICE_RATE
        has_drift = random.random() < cfg.DRIFT_DEVICE_RATE
        drift_offset_c = random.uniform(cfg.DRIFT_MIN_C, cfg.DRIFT_MAX_C) if has_drift else 0.0
        profiles[device_id] = {
            "uses_fahrenheit": uses_fahrenheit,
            "drift_offset_c": drift_offset_c,
        }
    return profiles


def generate_shipments_and_legs(n, products, routes, carriers, summary):
    shipment_rows = []
    leg_rows = []
    now = datetime.utcnow()

    for i in range(1, n + 1):
        shipment_id = f"SHIP-{i:05d}"
        product = products.sample(1).iloc[0]
        route = routes.sample(1).iloc[0]
        carrier = carriers.sample(1).iloc[0]
        ship_date = now - timedelta(days=random.randint(1, 180))

        missing_product = random.random() < cfg.MISSING_METADATA_RATE
        missing_route = random.random() < cfg.MISSING_METADATA_RATE
        if missing_product:
            summary["shipments_missing_product_ref"] += 1
        if missing_route:
            summary["shipments_missing_route_ref"] += 1

        shipment_rows.append(
            {
                "shipment_id": shipment_id,
                "product_id": None if missing_product else product["product_id"],
                "route_id": None if missing_route else route["route_id"],
                "carrier_id": carrier["carrier_id"],
                "ship_date": ship_date.date().isoformat(),
            }
        )

        num_legs = random.randint(cfg.MIN_LEGS_PER_SHIPMENT, cfg.MAX_LEGS_PER_SHIPMENT)
        leg_distance = route["distance_km"] / num_legs
        speed_kmh = SPEED_KMH[route["transport_mode"]]
        leg_duration_hours = max(leg_distance / speed_kmh, 0.5)

        is_cold_chain_break = random.random() < cfg.COLD_CHAIN_BREAK_RATE
        break_leg_seq = random.randint(1, num_legs) if is_cold_chain_break else None

        leg_start = ship_date
        for leg_seq in range(1, num_legs + 1):
            leg_end = leg_start + timedelta(hours=leg_duration_hours)
            leg_rows.append(
                {
                    "leg_id": f"{shipment_id}-LEG{leg_seq}",
                    "shipment_id": shipment_id,
                    "leg_sequence": leg_seq,
                    "device_id": f"DEV-{random.randint(1, DEVICE_POOL_SIZE):04d}",
                    "planned_distance_km": round(leg_distance, 1),
                    "leg_start_ts": leg_start,
                    "leg_end_ts": leg_end,
                    "is_final_leg": leg_seq == num_legs,
                    "has_cold_chain_break": leg_seq == break_leg_seq,
                    "_safe_temp_min_c": product["safe_temp_min_c"],
                    "_safe_temp_max_c": product["safe_temp_max_c"],
                }
            )
            leg_start = leg_end

    return pd.DataFrame(shipment_rows), pd.DataFrame(leg_rows)


def generate_sensor_readings(legs, device_profiles, summary):
    rows = []
    reading_counter = 0
    interval = timedelta(minutes=cfg.READING_INTERVAL_MINUTES)

    for _, leg in legs.iterrows():
        midpoint = (leg["_safe_temp_min_c"] + leg["_safe_temp_max_c"]) / 2
        spread = (leg["_safe_temp_max_c"] - leg["_safe_temp_min_c"]) / 6
        profile = device_profiles[leg["device_id"]]

        excursion_start = excursion_end = None
        if leg["has_cold_chain_break"]:
            leg_span = (leg["leg_end_ts"] - leg["leg_start_ts"]).total_seconds()
            excursion_start = leg["leg_start_ts"] + timedelta(seconds=random.uniform(0, leg_span * 0.6))
            excursion_end = excursion_start + timedelta(minutes=random.uniform(30, 90))

        ts = leg["leg_start_ts"]
        while ts <= leg["leg_end_ts"]:
            if random.random() < cfg.DROPOUT_RATE:
                summary["readings_dropped"] += 1
                ts += interval
                continue

            base_temp_c = midpoint + random.gauss(0, max(spread, 0.1))
            if excursion_start and excursion_start <= ts <= excursion_end:
                base_temp_c += random.uniform(5, 12)

            true_temp_c = base_temp_c + profile["drift_offset_c"]
            if profile["drift_offset_c"] != 0:
                summary["readings_from_drifted_devices"] += 1

            if profile["uses_fahrenheit"]:
                value = true_temp_c * 9 / 5 + 32
                unit = "F"
            else:
                value = true_temp_c
                unit = "C"

            reading_counter += 1
            reading_id = f"READ-{reading_counter:08d}"
            reading_ts = ts
            rows.append(
                {
                    "reading_id": reading_id,
                    "leg_id": leg["leg_id"],
                    "device_id": leg["device_id"],
                    "reading_ts": reading_ts,
                    "ingested_at": reading_ts + timedelta(seconds=random.uniform(5, 120)),
                    "temperature_value": round(value, 2),
                    "temperature_unit": unit,
                }
            )

            if random.random() < cfg.DUPLICATE_RATE:
                reading_counter += 1
                dup_ts = reading_ts + timedelta(seconds=random.uniform(1, 10))
                rows.append(
                    {
                        "reading_id": f"READ-{reading_counter:08d}",
                        "leg_id": leg["leg_id"],
                        "device_id": leg["device_id"],
                        "reading_ts": dup_ts,
                        "ingested_at": dup_ts + timedelta(seconds=random.uniform(5, 120)),
                        "temperature_value": round(value + random.uniform(-0.1, 0.1), 2),
                        "temperature_unit": unit,
                    }
                )
                summary["duplicate_readings_injected"] += 1

            ts += interval

    return pd.DataFrame(rows)


def generate_shipment_events(legs, summary):
    rows = []
    event_counter = 0

    for shipment_id, shipment_legs in legs.groupby("shipment_id"):
        shipment_legs = shipment_legs.sort_values("leg_sequence")
        out_of_sequence = random.random() < cfg.OUT_OF_SEQUENCE_RATE

        for _, leg in shipment_legs.iterrows():
            event_counter += 1
            event_type = "picked_up" if leg["leg_sequence"] == 1 else "arrived_checkpoint"
            event_ts = leg["leg_start_ts"]
            rows.append(
                {
                    "event_id": f"EVT-{event_counter:08d}",
                    "shipment_id": shipment_id,
                    "leg_id": leg["leg_id"],
                    "event_type": event_type,
                    "event_ts": event_ts,
                    "ingested_at": event_ts + timedelta(seconds=random.uniform(5, 120)),
                }
            )

            if leg["is_final_leg"]:
                event_counter += 1
                delivered_ts = leg["leg_end_ts"]
                if out_of_sequence:
                    # Simulates network lag: this event lands in the ingestion
                    # stream before some of the final leg's own sensor readings,
                    # even though it truly happened after them.
                    ingested_at = delivered_ts - timedelta(minutes=random.uniform(10, 30))
                    summary["shipments_with_out_of_sequence_delivery"] += 1
                else:
                    ingested_at = delivered_ts + timedelta(seconds=random.uniform(5, 120))

                rows.append(
                    {
                        "event_id": f"EVT-{event_counter:08d}",
                        "shipment_id": shipment_id,
                        "leg_id": leg["leg_id"],
                        "event_type": "delivered",
                        "event_ts": delivered_ts,
                        "ingested_at": ingested_at,
                    }
                )

    return pd.DataFrame(rows)


def write_summary(path, summary, counts):
    lines = ["Data quality injection summary", "=" * 32, ""]
    lines.append("Volumes:")
    for key, value in counts.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("Injected issues (spec section 3.1):")
    for key, value in summary.items():
        lines.append(f"  {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shipments", type=int, default=cfg.NUM_SHIPMENTS)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        Faker.seed(args.seed)

    summary = {
        "shipments_missing_product_ref": 0,
        "shipments_missing_route_ref": 0,
        "shipments_with_out_of_sequence_delivery": 0,
        "readings_dropped": 0,
        "duplicate_readings_injected": 0,
        "readings_from_drifted_devices": 0,
    }

    products = generate_products(cfg.NUM_PRODUCTS)
    carriers = generate_carriers(cfg.NUM_CARRIERS)
    routes = generate_routes(cfg.NUM_ROUTES)
    device_profiles = build_device_profiles(DEVICE_POOL_SIZE)

    shipments, legs = generate_shipments_and_legs(args.shipments, products, routes, carriers, summary)
    sensor_readings = generate_sensor_readings(legs, device_profiles, summary)
    shipment_events = generate_shipment_events(legs, summary)

    legs_out = legs.drop(columns=["_safe_temp_min_c", "_safe_temp_max_c"])

    from pathlib import Path

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    products.to_csv(out_dir / "products.csv", index=False)
    carriers.to_csv(out_dir / "carriers.csv", index=False)
    routes.to_csv(out_dir / "routes.csv", index=False)
    shipments.to_csv(out_dir / "shipments.csv", index=False)
    legs_out.to_csv(out_dir / "shipment_legs.csv", index=False)
    sensor_readings.to_csv(out_dir / "sensor_readings.csv", index=False)
    shipment_events.to_csv(out_dir / "shipment_events.csv", index=False)

    counts = {
        "products": len(products),
        "carriers": len(carriers),
        "routes": len(routes),
        "shipments": len(shipments),
        "shipment_legs": len(legs_out),
        "sensor_readings": len(sensor_readings),
        "shipment_events": len(shipment_events),
    }
    write_summary(out_dir / "data_quality_summary.txt", summary, counts)

    print(f"Wrote {sum(counts.values())} total rows across 7 files to {out_dir}/")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    print("\nInjected issues:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
