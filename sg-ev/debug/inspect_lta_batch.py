import json
import os

import requests
from dotenv import load_dotenv


load_dotenv()

LTA_API_KEY = os.getenv("LTA_API_KEY")

if not LTA_API_KEY:
    raise ValueError("LTA_API_KEY not found in .env")


LTA_ENDPOINT = (
    "https://datamall2.mytransport.sg/"
    "ltaodataservice/EVCBatch"
)


def main():
    print("=" * 60)
    print("LTA EV BATCH JSON INSPECTION")
    print("=" * 60)

    headers = {
        "AccountKey": LTA_API_KEY,
        "accept": "application/json",
    }

    # ---------------------------------------------------------
    # 1. Get latest batch URL
    # ---------------------------------------------------------
    print("\nRequesting latest LTA EV batch...")

    response = requests.get(
        LTA_ENDPOINT,
        headers=headers,
        timeout=60,
    )

    print("HTTP status:", response.status_code)

    response.raise_for_status()

    data = response.json()

    batch_url = data["value"][0]["Link"]

    print("Batch URL received successfully")

    # ---------------------------------------------------------
    # 2. Download batch JSON
    # ---------------------------------------------------------
    print("\nDownloading EV batch...")

    batch_response = requests.get(
        batch_url,
        timeout=60,
    )

    print(
        "Batch download HTTP status:",
        batch_response.status_code,
    )

    batch_response.raise_for_status()

    batch = batch_response.json()

    # ---------------------------------------------------------
    # 3. Get locations
    # ---------------------------------------------------------
    locations = batch.get("evLocationsData", [])

    print("Locations received:", len(locations))

    if not locations:
        print("ERROR: No locations found.")
        return

    # ---------------------------------------------------------
    # 4. Inspect first location
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("FIRST LOCATION")
    print("=" * 60)

    print(
        json.dumps(
            locations[0],
            indent=2,
            ensure_ascii=False,
        )
    )

    # ---------------------------------------------------------
    # 5. Inspect coordinate-related fields
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("TOP-LEVEL FIELDS")
    print("=" * 60)

    for key in locations[0].keys():
        print(key)

    print("\n" + "=" * 60)
    print("POSSIBLE COORDINATE FIELDS")
    print("=" * 60)

    for key, value in locations[0].items():
        key_lower = key.lower()

        if (
            "lat" in key_lower
            or "long" in key_lower
            or "lon" in key_lower
            or "position" in key_lower
            or "location" in key_lower
            or "coordinate" in key_lower
        ):
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
