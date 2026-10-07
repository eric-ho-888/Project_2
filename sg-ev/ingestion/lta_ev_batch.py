import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from google.cloud import bigquery


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

GCP_PROJECT = os.getenv(
    "GCP_PROJECT",
    "sg-ev-510713",
)

BQ_DATASET = os.getenv(
    "BQ_DATASET",
    "ev_raw",
)

BQ_TABLE = os.getenv(
    "BQ_TABLE",
    "ev_charging_raw",
)

LTA_BASE_URL = (
    "https://datamall2.mytransport.sg"
    "/ltaodataservice"
)

LTA_ENDPOINT = (
    f"{LTA_BASE_URL}/EVCBatch"
)

REQUEST_TIMEOUT = 60

TABLE_ID = (
    f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_float(value):
    """
    Convert a value to float.

    Returns None for:
    - None
    - empty strings
    - whitespace
    - invalid numeric values

    BigQuery will store None as NULL.
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def safe_int(value):
    """
    Convert a value to int.

    Returns None for invalid or empty values.
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value == "":
            return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def safe_string(value):
    """
    Convert a value to a cleaned string.

    Returns None for missing values.
    """

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


# ============================================================
# LTA API
# ============================================================

def get_lta_headers():
    """
    Build LTA DataMall request headers.

    The API key must be stored in .env.
    """

    api_key = os.getenv("LTA_API_KEY")

    if not api_key:
        raise RuntimeError(
            "LTA_API_KEY is not set in .env"
        )

    return {
        "AccountKey": api_key,
        "accept": "application/json",
    }


def get_batch_url():
    """
    Request the latest LTA EV charging batch URL.
    """

    print(
        "Requesting latest LTA EV charging batch..."
    )

    headers = get_lta_headers()

    response = requests.get(
        LTA_ENDPOINT,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    print(
        f"HTTP status: {response.status_code}"
    )

    response.raise_for_status()

    data = response.json()

    print("LTA response received")

    # --------------------------------------------------------
    # Extract batch URL
    # --------------------------------------------------------

    batch_url = None

    if isinstance(data, dict):

        # Common LTA response structure
        if "value" in data:
            value = data["value"]

            if isinstance(value, list) and value:
                first = value[0]

                if isinstance(first, dict):
                    batch_url = (
                        first.get("Link")
                        or first.get("link")
                        or first.get("URL")
                        or first.get("url")
                    )

        # Alternative response structure
        if not batch_url:
            batch_url = (
                data.get("Link")
                or data.get("link")
                or data.get("URL")
                or data.get("url")
            )

    if not batch_url:
        raise RuntimeError(
            "Could not find EV batch URL in "
            "LTA response."
        )

    print("Batch URL received successfully")

    return batch_url


def download_batch(batch_url):
    """
    Download the latest EV charging batch JSON.
    """

    print()
    print("Downloading EV batch...")

    response = requests.get(
        batch_url,
        timeout=REQUEST_TIMEOUT,
    )

    print(
        f"Batch download HTTP status: "
        f"{response.status_code}"
    )

    response.raise_for_status()

    data = response.json()

    print(
        "EV batch downloaded successfully"
    )

    return data


# ============================================================
# DATA EXTRACTION
# ============================================================

def get_locations(data):
    """
    Extract the EV location list from the LTA batch response.
    """

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        raise RuntimeError(
            "Unexpected LTA batch response format."
        )

    # Current LTA EV batch structure
    locations = data.get(
        "evLocationsData"
    )

    if isinstance(locations, list):
        return locations

    # Fallback structures
    for key in [
        "locations",
        "Locations",
        "value",
        "Value",
    ]:

        value = data.get(key)

        if isinstance(value, list):
            return value

    raise RuntimeError(
        "Could not find locations in LTA batch."
    )

# ============================================================
# FLATTEN LTA DATA
# ============================================================

def flatten_batch(data):
    """
    Flatten the nested LTA EV charging batch.

    Grain:
        One row per EV charging point / EV ID.
    """

    locations = get_locations(data)

    print(f"Locations received: {len(locations)}")

    rows = []

    last_updated_time = data.get("LastUpdatedTime")

    ingestion_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    for location in locations:

        if not isinstance(location, dict):
            continue

        address = safe_string(
            location.get("address")
        )

        station_name = safe_string(
            location.get("name")
        )

        longitude = safe_float(
            location.get("longtitude")
        )

        latitude = safe_float(
            location.get("latitude")
        )

        postal_code = safe_string(
            location.get("postalCode")
        )

        charging_points = (
            location.get("chargingPoints")
            or location.get("chargingPoint")
            or location.get("charging_points")
            or []
        )

        if isinstance(charging_points, dict):
            charging_points = [charging_points]

        elif not isinstance(charging_points, list):
            charging_points = []

        for charging_point in charging_points:

            if not isinstance(charging_point, dict):
                continue

            charger_status = safe_int(
                charging_point.get("status")
            )

            operating_hours = safe_string(
                charging_point.get("operatingHours")
            )

            operator = safe_string(
                charging_point.get("operator")
            )

            position = safe_string(
                charging_point.get("position")
            )

            charging_point_name = safe_string(
                charging_point.get("name")
            )

            plug_types = (
                charging_point.get("plugTypes")
                or charging_point.get("plugType")
                or charging_point.get("plug_types")
                or []
            )

            if isinstance(plug_types, dict):
                plug_types = [plug_types]

            elif isinstance(plug_types, str):
                plug_types = [
                    {
                        "plugType": plug_types
                    }
                ]

            elif not isinstance(plug_types, list):
                plug_types = []

            for plug in plug_types:

                if isinstance(plug, str):
                    plug = {
                        "plugType": plug
                    }

                if not isinstance(plug, dict):
                    continue

                plug_type = safe_string(
                    plug.get("plugType")
                )

                price = safe_float(
                    plug.get("price")
                )

                current = safe_string(
                    plug.get("current")
                )

                power_rating_kw = safe_float(
                    plug.get("powerRating")
                )

                price_type = safe_string(
                    plug.get("priceType")
                )

                ev_ids = (
                    plug.get("evIds")
                    or charging_point.get("evIds")
                    or []
                )

                if isinstance(ev_ids, dict):
                    ev_ids = [ev_ids]

                elif not isinstance(ev_ids, list):
                    ev_ids = []

                for ev_id in ev_ids:

                    if not isinstance(ev_id, dict):
                        continue

                    ev_cp_id = (
                        ev_id.get("evCpId")
                        or ev_id.get("evCPId")
                        or ev_id.get("ev_cp_id")
                        or ev_id.get("id")
                    )

                    ev_cp_id = safe_string(
                        ev_cp_id
                    )

                    ev_id_status = safe_int(
                        ev_id.get("status")
                    )

                    row = {
                        "last_updated_time": last_updated_time,
                        "address": address,
                        "station_name": station_name,
                        "longitude": longitude,
                        "latitude": latitude,
                        "postal_code": postal_code,
                        "charger_status": charger_status,
                        "operating_hours": operating_hours,
                        "operator": operator,
                        "position": position,
                        "charging_point_name": charging_point_name,
                        "plug_type": plug_type,
                        "price": price,
                        "current": current,
                        "power_rating_kw": power_rating_kw,
                        "price_type": price_type,
                        "ev_cp_id": ev_cp_id,
                        "ev_id_status": ev_id_status,
                        "ingestion_timestamp": ingestion_timestamp,
                    }

                    rows.append(row)

    print(f"Flattened rows: {len(rows)}")

    if not rows:
        raise RuntimeError(
            "No rows were generated from the LTA batch."
        )

    return rows


# ============================================================
# BIGQUERY
# ============================================================

def ensure_bigquery_table(client):
    """
    Create the raw table if it does not exist.
    """

    schema = [

        bigquery.SchemaField(
            "last_updated_time",
            "TIMESTAMP",
        ),

        bigquery.SchemaField(
            "address",
            "STRING",
        ),

        bigquery.SchemaField(
            "station_name",
            "STRING",
        ),

        bigquery.SchemaField(
            "longitude",
            "FLOAT64",
        ),

        bigquery.SchemaField(
            "latitude",
            "FLOAT64",
        ),

        bigquery.SchemaField(
            "postal_code",
            "STRING",
        ),

        bigquery.SchemaField(
            "charger_status",
            "INT64",
        ),

        bigquery.SchemaField(
            "operating_hours",
            "STRING",
        ),

        bigquery.SchemaField(
            "operator",
            "STRING",
        ),

        bigquery.SchemaField(
            "position",
            "STRING",
        ),

        bigquery.SchemaField(
            "charging_point_name",
            "STRING",
        ),

        bigquery.SchemaField(
            "plug_type",
            "STRING",
        ),

        bigquery.SchemaField(
            "price",
            "FLOAT64",
        ),

        bigquery.SchemaField(
            "current",
            "STRING",
        ),

        bigquery.SchemaField(
            "power_rating_kw",
            "FLOAT64",
        ),

        bigquery.SchemaField(
            "price_type",
            "STRING",
        ),

        bigquery.SchemaField(
            "ev_cp_id",
            "STRING",
        ),

        bigquery.SchemaField(
            "ev_id_status",
            "INT64",
        ),

        bigquery.SchemaField(
            "ingestion_timestamp",
            "TIMESTAMP",
        ),
    ]

    table = bigquery.Table(
        TABLE_ID,
        schema=schema,
    )

    table = client.create_table(
        table,
        exists_ok=True,
    )

    return table


def insert_into_bigquery(rows):
    """
    Insert flattened rows into BigQuery.
    """

    print()
    print("Connecting to BigQuery...")

    client = bigquery.Client(
        project=GCP_PROJECT
    )

    print(
        f"BigQuery table: {TABLE_ID}"
    )

    ensure_bigquery_table(
        client
    )

    print(
        f"Rows to insert: {len(rows)}"
    )

    errors = client.insert_rows_json(
        TABLE_ID,
        rows,
    )

    if errors:

        print()
        print(
            "============================================================"
        )
        print(
            "BIGQUERY INSERTION ERRORS"
        )
        print(
            "============================================================"
        )

        print(
            f"Number of errors: {len(errors)}"
        )

        for index, error in enumerate(
            errors[:10],
            start=1
        ):

            print()
            print(
                f"Error {index}:"
            )

            print(error)

        raise RuntimeError(
            "BigQuery insertion failed. "
            "See the errors above."
        )

    print()
    print(
        "BigQuery insertion successful."
    )

    print(
        f"Rows inserted: {len(rows)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "============================================================"
    )

    print(
        "LTA EV CHARGING BATCH INGESTION"
    )

    print(
        "============================================================"
    )

    try:

        # ----------------------------------------------------
        # 1. Get latest batch URL
        # ----------------------------------------------------

        batch_url = get_batch_url()

        # ----------------------------------------------------
        # 2. Download batch
        # ----------------------------------------------------

        batch_data = download_batch(
            batch_url
        )

        # ----------------------------------------------------
        # 3. Flatten data
        # ----------------------------------------------------

        rows = flatten_batch(
            batch_data
        )

        # ----------------------------------------------------
        # 4. Insert into BigQuery
        # ----------------------------------------------------

        insert_into_bigquery(
            rows
        )

        # ----------------------------------------------------
        # 5. Completed
        # ----------------------------------------------------

        print()
        print(
            "============================================================"
        )

        print(
            "LTA EV CHARGING BATCH INGESTION COMPLETE"
        )

        print(
            "============================================================"
        )

    except Exception as exc:

        print()
        print(
            "============================================================"
        )

        print(
            "INGESTION FAILED"
        )

        print(
            "============================================================"
        )

        print(
            f"Error: {exc}"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()