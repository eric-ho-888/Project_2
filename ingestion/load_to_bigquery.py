import os
import json
import pandas as pd

from dotenv import load_dotenv
from google.cloud import bigquery

# ----------------------------------------
# 1. Load environment variables
# ----------------------------------------

load_dotenv()

project_id = os.getenv("GCP_PROJECT_ID")
dataset_id = os.getenv("BQ_RAW_DATASET")
table_name = os.getenv("BQ_RAW_TABLE")


# ----------------------------------------
# 2. Load LTA JSON
# ----------------------------------------

with open("ev_charging.json", "r", encoding="utf-8") as f:
    data = json.load(f)


# ----------------------------------------
# 3. Inspect data
# ----------------------------------------

print("Data type:", type(data))

if isinstance(data, list):
    print("Number of records:", len(data))

elif isinstance(data, dict):
    print("Dictionary keys:", data.keys())


# ----------------------------------------
# 4. Create DataFrame
# ----------------------------------------

# TEMPORARY:
# This assumes data is already a flat list.
# We will replace this with the correct
# LTA flattening logic after inspecting
# your actual JSON structure.

df = pd.DataFrame(data)


# ----------------------------------------
# 5. Add ingestion timestamp
# ----------------------------------------

df["ingestion_timestamp"] = pd.Timestamp.now(tz="UTC")


# ----------------------------------------
# 6. Create BigQuery client
# ----------------------------------------

client = bigquery.Client(project=project_id)


# ----------------------------------------
# 7. BigQuery table
# ----------------------------------------

table_id = f"{project_id}.{dataset_id}.{table_name}"


# ----------------------------------------
# 8. Configure upload
# ----------------------------------------

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE"
)


# ----------------------------------------
# 9. Upload
# ----------------------------------------

job = client.load_table_from_dataframe(
    df,
    table_id,
    job_config=job_config
)

job.result()


# ----------------------------------------
# 10. Verify
# ----------------------------------------

print("Upload successful!")
print(f"Rows loaded: {len(df):,}")
print(f"BigQuery table: {table_id}")