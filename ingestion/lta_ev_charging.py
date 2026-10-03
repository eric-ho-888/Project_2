import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_KEY = os.getenv("LTA_ACCOUNT_KEY")

# LTA EVCBatch API
api_url = "https://datamall2.mytransport.sg/ltaodataservice/EVCBatch"

headers = {
    "AccountKey": ACCOUNT_KEY,
    "accept": "application/json"
}

# ------------------------------------------------
# 1. Request the latest EV charging batch
# ------------------------------------------------

response = requests.get(
    api_url,
    headers=headers,
    timeout=60
)

response.raise_for_status()

data = response.json()

print("LTA API request successful")
print("Status:", response.status_code)


# ------------------------------------------------
# 2. Extract temporary download URL
# ------------------------------------------------

download_url = data["value"][0]["Link"]

print("Download URL received")
print(download_url[:150] + "...")


# ------------------------------------------------
# 3. Download EV charging JSON
# ------------------------------------------------

file_response = requests.get(
    download_url,
    timeout=60
)

file_response.raise_for_status()


# ------------------------------------------------
# 4. Save file
# ------------------------------------------------

output_file = "ev_charging.json"

with open(output_file, "wb") as f:
    f.write(file_response.content)

print(f"Downloaded successfully: {output_file}")
print(f"File size: {len(file_response.content):,} bytes")

import json

with open("ev_charging.json", "r", encoding="utf-8") as f:
    ev_data = json.load(f)

print(type(ev_data))
print(json.dumps(ev_data, indent=2)[:5000])