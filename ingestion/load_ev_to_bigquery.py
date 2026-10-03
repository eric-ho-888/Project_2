import os
import json
import pandas as pd

from dotenv import load_dotenv
from google.cloud import bigquery


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

project_id = os.getenv("GCP_PROJECT_ID")
dataset_id = os.getenv("BQ_RAW_DATASET")
table_name = os.getenv("BQ_RAW_TABLE")


# Check configuration
if not project_id:
    raise ValueError("GCP_PROJECT_ID is missing from .env")

if not dataset_id:
    raise ValueError("BQ_RAW_DATASET is missing from .env")

if not table_name:
    raise ValueError("BQ_RAW_TABLE is missing from .env")


# ============================================================
# 2. LOAD LTA JSON
# ============================================================

json_file = "ev_charging.json"

with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)


print("LTA JSON loaded successfully")


# ============================================================
# 3. GET LAST UPDATED TIME
# ============================================================

last_updated_time = data.get("LastUpdatedTime")

print("LTA LastUpdatedTime:", last_updated_time)


# ============================================================
# 4. GET LOCATIONS
# ============================================================

locations = data.get("evLocationsData", [])

print("Number of locations:", len(locations))


# ============================================================
# 5. FLATTEN NESTED JSON
# ============================================================

records = []


for location in locations:

    # --------------------------------------------------------
    # Location-level information
    # --------------------------------------------------------

    address = location.get("address")
    station_name = location.get("name")
    longitude = location.get("longtitude")
    latitude = location.get("latitude")
    postal_code = location.get("postalCode")

    charging_points = location.get("chargingPoints", [])


    # --------------------------------------------------------
    # Charging point
    # --------------------------------------------------------

    for charging_point in charging_points:

        charger_status = charging_point.get("status")
        operating_hours = charging_point.get("operatingHours")
        operator = charging_point.get("operator")
        position = charging_point.get("position")

        charging_point_name = charging_point.get("name")

        plug_types = charging_point.get("plugTypes", [])


        # ----------------------------------------------------
        # Plug type
        # ----------------------------------------------------

        for plug in plug_types:

            plug_type = plug.get("plugType")
            price = plug.get("price")
            current = plug.get("current")
            power_rating = plug.get("powerRating")
            price_type = plug.get("priceType")

            ev_ids = plug.get("evIds", [])


            # ------------------------------------------------
            # EV charging connector
            # ------------------------------------------------

            for ev in ev_ids:

                ev_cp_id = ev.get("evCpId")
                ev_id_status = ev.get("status")


                records.append({
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
                    "power_rating_kw": power_rating,
                    "price_type": price_type,

                    "ev_cp_id": ev_cp_id,
                    "ev_id_status": ev_id_status
                })


# ============================================================
# 6. CREATE DATAFRAME
# ============================================================

df = pd.DataFrame(records)


print()
print("Flattening complete")
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ============================================================
# 7. CONVERT DATA TYPES
# ============================================================

df["last_updated_time"] = pd.to_datetime(
    df["last_updated_time"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["price"] = pd.to_numeric(
    df["price"],
    errors="coerce"
)

df["power_rating_kw"] = pd.to_numeric(
    df["power_rating_kw"],
    errors="coerce"
)

df["charger_status"] = pd.to_numeric(
    df["charger_status"],
    errors="coerce"
)

df["ev_id_status"] = pd.to_numeric(
    df["ev_id_status"],
    errors="coerce"
)


# ============================================================
# 8. ADD INGESTION TIMESTAMP
# ============================================================

df["ingestion_timestamp"] = pd.Timestamp.now(tz="UTC")


# ============================================================
# 9. DISPLAY SAMPLE
# ============================================================

print()
print("Sample data:")
print(df.head())


print()
print("Data types:")
print(df.dtypes)


# ============================================================
# 10. CONNECT TO BIGQUERY
# ============================================================

client = bigquery.Client(
    project=project_id
)


# ============================================================
# 11. BIGQUERY TABLE ID
# ============================================================

table_id = (
    f"{project_id}."
    f"{dataset_id}."
    f"{table_name}"
)

print()
print("BigQuery table:")
print(table_id)


# ============================================================
# 12. DEFINE BIGQUERY SCHEMA
# ============================================================

schema = [

    bigquery.SchemaField(
        "last_updated_time",
        "TIMESTAMP"
    ),

    bigquery.SchemaField(
        "address",
        "STRING"
    ),

    bigquery.SchemaField(
        "station_name",
        "STRING"
    ),

    bigquery.SchemaField(
        "longitude",
        "FLOAT64"
    ),

    bigquery.SchemaField(
        "latitude",
        "FLOAT64"
    ),

    bigquery.SchemaField(
        "postal_code",
        "STRING"
    ),

    bigquery.SchemaField(
        "charger_status",
        "INT64"
    ),

    bigquery.SchemaField(
        "operating_hours",
        "STRING"
    ),

    bigquery.SchemaField(
        "operator",
        "STRING"
    ),

    bigquery.SchemaField(
        "position",
        "STRING"
    ),

    bigquery.SchemaField(
        "charging_point_name",
        "STRING"
    ),

    bigquery.SchemaField(
        "plug_type",
        "STRING"
    ),

    bigquery.SchemaField(
        "price",
        "FLOAT64"
    ),

    bigquery.SchemaField(
        "current",
        "STRING"
    ),

    bigquery.SchemaField(
        "power_rating_kw",
        "FLOAT64"
    ),

    bigquery.SchemaField(
        "price_type",
        "STRING"
    ),

    bigquery.SchemaField(
        "ev_cp_id",
        "STRING"
    ),

    bigquery.SchemaField(
        "ev_id_status",
        "INT64"
    ),

    bigquery.SchemaField(
        "ingestion_timestamp",
        "TIMESTAMP"
    )
]


# ============================================================
# 13. BIGQUERY LOAD CONFIGURATION
# ============================================================

job_config = bigquery.LoadJobConfig(
    schema=schema,
    write_disposition="WRITE_TRUNCATE"
)


# ============================================================
# 14. LOAD DATAFRAME INTO BIGQUERY
# ============================================================

print()
print("Uploading data to BigQuery...")

job = client.load_table_from_dataframe(
    df,
    table_id,
    job_config=job_config
)

job.result()


# ============================================================
# 15. SUCCESS
# ============================================================

print()
print("========================================")
print("UPLOAD SUCCESSFUL")
print("========================================")

print("Rows loaded:", len(df))
print("BigQuery table:", table_id)