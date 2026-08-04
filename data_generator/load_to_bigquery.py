"""One-off loader: pushes data_generator/output/*.csv into the BigQuery `raw` dataset.

Not a dbt model and not part of the regular pipeline - run manually after
`python generate.py` whenever the raw dataset needs (re)loading. Uses schema
autodetection since the bronze staging models expect properly typed columns
(TIMESTAMP, DATE, FLOAT, BOOL), not everything as STRING.

Requires GCP_PROJECT (and GOOGLE_APPLICATION_CREDENTIALS pointing at the
service account keyfile) set in the environment - see docs/session_handoff.md.
"""

import os
import pathlib

from google.cloud import bigquery

PROJECT = os.environ["GCP_PROJECT"]
DATASET = "raw"
LOCATION = "US"
OUTPUT_DIR = pathlib.Path(__file__).parent / "output"

TABLES = [
    "products",
    "carriers",
    "routes",
    "shipments",
    "shipment_legs",
    "sensor_readings",
    "shipment_events",
]


def main():
    client = bigquery.Client(project=PROJECT)

    dataset_ref = bigquery.DatasetReference(PROJECT, DATASET)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset {PROJECT}.{DATASET} ready")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    for table_name in TABLES:
        csv_path = OUTPUT_DIR / f"{table_name}.csv"
        table_ref = dataset_ref.table(table_name)
        with open(csv_path, "rb") as f:
            load_job = client.load_table_from_file(f, table_ref, job_config=job_config)
        load_job.result()
        table = client.get_table(table_ref)
        print(f"Loaded {table_name}: {table.num_rows} rows, {len(table.schema)} columns")


if __name__ == "__main__":
    main()
