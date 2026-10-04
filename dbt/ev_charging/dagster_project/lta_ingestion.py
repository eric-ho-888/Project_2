import os
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
import requests
from dagster import AssetExecutionContext, asset
from google.cloud import bigquery


LTA_URL = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"

GCP_PROJECT_ID = "sg-ev-charging-analytics"
BQ_DATASET = "ev_raw"
BQ_TABLE = "ev_charging_raw"

TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"


@asset
def lta_ev_charging_raw(context: AssetExecutionContext):
    """
    Download the latest LTA EV charging batch and append it
    to BigQuery as a new ingestion snapshot.
    """

    account_key = os.getenv("LTA_ACCOUNT_KEY")

    if not account_key:
        raise RuntimeError(
            "LTA_ACCOUNT_KEY environment variable is not set."
        )

    # ---------------------------------------------------------
    # 1. Request latest LTA EV batch
    # ---------------------------------------------------------

    headers = {
        "AccountKey": account_key,
        "accept": "application/json",
    }

    context.log.info("Requesting latest LTA EV charging batch...")

    response = requests.get(
        LTA_URL,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("value"):
        raise RuntimeError("LTA API returned no EV batch.")

    batch_url = data["value"][0]["Link"]

    context.log.info(
        f"LTA batch URL received: {batch_url[:100]}..."
    )

    # ---------------------------------------------------------
    # 2. Download batch file
    # ---------------------------------------------------------

    file_response = requests.get(
        batch_url,
        timeout=120,
    )

    file_response.raise_for_status()

    context.log.info(
        f"Downloaded {len(file_response.content):,} bytes."
    )

    # ---------------------------------------------------------
    # 3. Read CSV
    # ---------------------------------------------------------

    df = pd.read_csv(
        BytesIO(file_response.content)
    )

    context.log.info(
        f"LTA batch contains {len(df):,} rows."
    )

    # ---------------------------------------------------------
    # 4. Normalize column names
    # ---------------------------------------------------------

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    context.log.info(
        f"Columns: {list(df.columns)}"
    )

    # ---------------------------------------------------------
    # 5. Add ingestion timestamp
    # ---------------------------------------------------------

    ingestion_time = datetime.now(timezone.utc)

    df["ingestion_timestamp"] = ingestion_time

    # ---------------------------------------------------------
    # 6. Rename columns to match BigQuery raw table
    # ---------------------------------------------------------

    rename_map = {
        "lastupdatedtime": "last_updated_time",
        "last_updated_time": "last_updated_time",
        "postalcode": "postal_code",
        "chargerstatus": "charger_status",
        "operatinghours": "operating_hours",
        "chargingpointname": "charging_point_name",
        "plugtype": "plug_type",
        "powerratingkw": "power_rating_kw",
        "pricetype": "price_type",
        "evcpid": "ev_cp_id",
        "evidstatus": "ev_id_status",
    }

    df = df.rename(columns=rename_map)

    # ---------------------------------------------------------
    # 7. Keep only columns used by raw BigQuery table
    # ---------------------------------------------------------

    expected_columns = [
        "last_updated_time",
        "address",
        "station_name",
        "longitude",
        "latitude",
        "postal_code",
        "charger_status",
        "operating_hours",
        "operator",
        "position",
        "charging_point_name",
        "plug_type",
        "price",
        "current",
        "power_rating_kw",
        "price_type",
        "ev_cp_id",
        "ev_id_status",
        "ingestion_timestamp",
    ]

    missing_columns = [
        column
        for column in expected_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise RuntimeError(
            f"Missing expected columns: {missing_columns}"
        )

    df = df[expected_columns]

    # ---------------------------------------------------------
    # 8. BigQuery data types
    # ---------------------------------------------------------

    df["last_updated_time"] = pd.to_datetime(
        df["last_updated_time"],
        errors="coerce",
        utc=True,
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce",
    )

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce",
    )

    df["charger_status"] = pd.to_numeric(
        df["charger_status"],
        errors="coerce",
    ).astype("Int64")

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce",
    )

    df["power_rating_kw"] = pd.to_numeric(
        df["power_rating_kw"],
        errors="coerce",
    )

    df["ev_id_status"] = pd.to_numeric(
        df["ev_id_status"],
        errors="coerce",
    ).astype("Int64")

    # ---------------------------------------------------------
    # 9. Load into BigQuery
    # ---------------------------------------------------------

    client = bigquery.Client(
        project=GCP_PROJECT_ID
    )

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    context.log.info(
        f"Loading {len(df):,} rows into {TABLE_ID}..."
    )

    job = client.load_table_from_dataframe(
        df,
        TABLE_ID,
        job_config=job_config,
    )

    job.result()

    context.log.info(
        f"Successfully loaded {len(df):,} rows."
    )

    return {
        "rows_loaded": len(df),
        "table": TABLE_ID,
        "ingestion_timestamp": ingestion_time.isoformat(),
    }
