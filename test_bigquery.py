import json

with open("ev_charging.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(json.dumps(data, indent=2)[:10000])