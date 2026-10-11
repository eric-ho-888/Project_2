from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
from google.cloud import bigquery


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
PROJECT_ID = "sg-ev-510713"
DATASET_ID = "ev_analytics"

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = bigquery.Client(project=PROJECT_ID)


def load_query(sql: str) -> pd.DataFrame:
    """Run a BigQuery query and return a Pandas DataFrame."""
    return client.query(sql).to_dataframe(
        create_bqstorage_client=False
    )


def save_chart(filename: str) -> None:
    """Save the current Matplotlib figure."""
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / filename,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()
    print(f"Chart saved: {filename}")


# ---------------------------------------------------------
# 1. Load dbt analytics tables
# ---------------------------------------------------------
print("Loading regional summary from BigQuery...")

regional = load_query(f"""
    SELECT *
    FROM `{PROJECT_ID}.{DATASET_ID}.ev_charging_summary`
    ORDER BY total_charging_points DESC
""")

print("Loading fact table from BigQuery...")

fact = load_query(f"""
    SELECT
        ev_cp_id,
        station_name,
        operator,
        region,
        plug_type,
        current_type,
        power_rating_kw,
        price,
        price_type,
        charger_status
    FROM `{PROJECT_ID}.{DATASET_ID}.fct_ev_charging_points`
""")

if regional.empty or fact.empty:
    raise RuntimeError(
        "A BigQuery result is empty. Check the dbt tables first."
    )

print(f"Regional summary rows: {len(regional):,}")
print(f"Fact table rows: {len(fact):,}")


# ---------------------------------------------------------
# 2. Pandas: business metrics
# ---------------------------------------------------------
print("\nCalculating business metrics with Pandas...")

total_charging_points = int(regional["total_charging_points"].sum())
available = int(regional["available_charging_points"].sum())
occupied = int(regional["occupied_charging_points"].sum())
unknown = int(regional["charging_points_with_unknown_status"].sum())

ac_total = int(regional["ac_charging_points"].sum())
dc_total = int(regional["dc_charging_points"].sum())

average_power = fact["power_rating_kw"].mean()
average_price = fact["price"].mean()

kpis = pd.DataFrame([
    {"metric": "total_charging_points", "value": total_charging_points},
    {"metric": "available_charging_points", "value": available},
    {"metric": "occupied_charging_points", "value": occupied},
    {"metric": "unknown_status_charging_points", "value": unknown},
    {"metric": "ac_charging_points", "value": ac_total},
    {"metric": "dc_charging_points", "value": dc_total},
    {"metric": "average_power_rating_kw", "value": average_power},
    {"metric": "average_price_per_kwh", "value": average_price},
])

kpis.to_csv(OUTPUT_DIR / "analysis_results.csv", index=False)
regional.to_csv(OUTPUT_DIR / "regional_summary.csv", index=False)

print(kpis.to_string(index=False))


# ---------------------------------------------------------
# 3. Polars: independent aggregation and cross-check
# ---------------------------------------------------------
print("\nCross-checking charging-point counts with Polars...")

polars_fact = pl.from_pandas(fact)

polars_region_counts = (
    polars_fact
    .group_by("region")
    .agg(pl.len().alias("polars_charging_point_rows"))
    .sort("region")
)

pandas_region_counts = (
    fact.groupby("region", dropna=False)
    .size()
    .rename("pandas_charging_point_rows")
    .reset_index()
)

polars_check = (
    pandas_region_counts
    .merge(
        polars_region_counts.to_pandas(),
        on="region",
        how="outer",
    )
    .fillna(0)
)

polars_check["counts_match"] = (
    polars_check["pandas_charging_point_rows"]
    == polars_check["polars_charging_point_rows"]
)

polars_check.to_csv(
    OUTPUT_DIR / "pandas_polars_validation.csv",
    index=False,
)

print(polars_check.to_string(index=False))

if not polars_check["counts_match"].all():
    raise RuntimeError(
        "Pandas and Polars charging-point counts do not match."
    )

print("Pandas and Polars counts match.")


# ---------------------------------------------------------
# 4. Matplotlib: regional charging-point distribution
# ---------------------------------------------------------
plot_data = regional.sort_values("total_charging_points")

plt.figure(figsize=(10, 6))
plt.barh(plot_data["region"], plot_data["total_charging_points"])
plt.xlabel("Number of charging points")
plt.ylabel("Region")
plt.title("EV Charging Points by Region")
plt.grid(axis="x", alpha=0.25)
save_chart("regional_charging_points.png")


# ---------------------------------------------------------
# 5. Matplotlib: charging-point status by region
# ---------------------------------------------------------
status_columns = [
    "available_charging_points",
    "occupied_charging_points",
    "charging_points_with_unknown_status",
]

status_data = regional.set_index("region")[status_columns]
status_data = status_data.rename(columns={
    "available_charging_points": "Available",
    "occupied_charging_points": "Occupied",
    "charging_points_with_unknown_status": "Unknown status",
})

ax = status_data.plot(
    kind="bar",
    stacked=True,
    figsize=(11, 6),
)

ax.set_title("Charging Point Status by Region")
ax.set_xlabel("Region")
ax.set_ylabel("Number of charging points")
ax.legend(title="Status")
ax.grid(axis="y", alpha=0.25)
plt.xticks(rotation=30, ha="right")
save_chart("charging_point_status_by_region.png")


# ---------------------------------------------------------
# 6. Matplotlib: AC vs DC charging-point mix
# ---------------------------------------------------------
plt.figure(figsize=(8, 5))
plt.bar(
    ["AC", "DC"],
    [ac_total, dc_total],
)
plt.ylabel("Number of charging points")
plt.title("AC vs DC Charging Point Distribution")
plt.grid(axis="y", alpha=0.25)
save_chart("ac_dc_distribution.png")


# ---------------------------------------------------------
# 7. Matplotlib: top 10 operators
# ---------------------------------------------------------
operator_data = (
    fact.assign(
        operator=fact["operator"].fillna("Unknown operator")
    )
    .groupby("operator")
    .size()
    .sort_values(ascending=False)
    .head(10)
    .sort_values()
)

operator_data.rename("charging_points").to_csv(
    OUTPUT_DIR / "operator_summary.csv"
)

plt.figure(figsize=(10, 6))
plt.barh(operator_data.index, operator_data.values)
plt.xlabel("Number of charging points")
plt.ylabel("Operator")
plt.title("Top 10 EV Charging Operators")
plt.grid(axis="x", alpha=0.25)
save_chart("operator_distribution.png")


# ---------------------------------------------------------
# 8. Matplotlib: average power rating by region
# ---------------------------------------------------------
power_data = (
    fact.groupby("region", dropna=False)["power_rating_kw"]
    .mean()
    .dropna()
    .sort_values()
)

power_data.rename("average_power_rating_kw").to_csv(
    OUTPUT_DIR / "power_rating_by_region.csv"
)

plt.figure(figsize=(10, 6))
plt.barh(power_data.index.astype(str), power_data.values)
plt.xlabel("Average power rating (kW)")
plt.ylabel("Region")
plt.title("Average Charging-Point Power Rating by Region")
plt.grid(axis="x", alpha=0.25)
save_chart("power_rating_by_region.png")


# ---------------------------------------------------------
# 9. Run summary
# ---------------------------------------------------------
print("\nAnalytics completed successfully.")
print(f"Output directory: {OUTPUT_DIR}")
print("Generated files:")
for path in sorted(OUTPUT_DIR.iterdir()):
    if path.is_file():
        print(f"  - {path.name}")
