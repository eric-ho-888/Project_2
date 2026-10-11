from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "sg-ev-510713"
TABLE_ID = f"{PROJECT_ID}.ev_analytics.ev_operator_pricing"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            operator,
            charging_points,
            charging_points_with_positive_price,
            avg_price_per_kwh,
            min_price_per_kwh,
            max_price_per_kwh
        FROM `{TABLE_ID}`
        ORDER BY avg_price_per_kwh
    """

    df = client.query(query).to_dataframe()

    if df.empty:
        raise ValueError("The BigQuery pricing table contains no rows.")

    df["operator_short"] = (
        df["operator"]
        .str.replace(" PTE. LTD.", "", regex=False)
        .str.replace(" PRIVATE LIMITED", "", regex=False)
        .str.replace(" PTE LTD", "", regex=False)
    )

    plt.rcParams.update({
        "figure.figsize": (12, 7),
        "font.size": 10,
        "axes.titlesize": 16,
        "axes.labelsize": 11,
    })

    # Chart 1: Average positive price per kWh
    price_df = df.sort_values("avg_price_per_kwh", ascending=True)

    fig, ax = plt.subplots()
    bars = ax.barh(
        price_df["operator_short"],
        price_df["avg_price_per_kwh"],
    )
    ax.bar_label(bars, fmt="S$%.3f", padding=4)
    ax.set_title("Singapore EV Charging Prices by Operator")
    ax.set_xlabel("Average positive price (S$/kWh)")
    ax.set_ylabel("Charging operator")
    ax.set_xlim(0, price_df["avg_price_per_kwh"].max() * 1.22)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01, 0.01,
        "Source: LTA DataMall EV Charging Points Batch | "
        "kWh-priced records; positive prices only",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(
        OUTPUT_DIR / "ev_operator_average_price.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)

    # Chart 2: Network size by operator
    size_df = df.sort_values("charging_points", ascending=True)

    fig, ax = plt.subplots()
    bars = ax.barh(
        size_df["operator_short"],
        size_df["charging_points"],
    )
    ax.bar_label(bars, fmt="%.0f", padding=4)
    ax.set_title("EV Charging Network Size by Operator")
    ax.set_xlabel("Distinct charging-point IDs")
    ax.set_ylabel("Charging operator")
    ax.set_xlim(0, size_df["charging_points"].max() * 1.18)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01, 0.01,
        "Source: LTA DataMall EV Charging Points Batch | "
        "Operators with at least 100 charging-point IDs",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(
        OUTPUT_DIR / "ev_operator_network_size.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)

    # Chart 3: Average price versus network size
    fig, ax = plt.subplots()
    ax.scatter(
        df["charging_points"],
        df["avg_price_per_kwh"],
        s=85,
    )

    for _, row in df.iterrows():
        ax.annotate(
            row["operator_short"],
            (
                row["charging_points"],
                row["avg_price_per_kwh"],
            ),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title("EV Charging Price vs Network Size")
    ax.set_xlabel("Distinct charging-point IDs")
    ax.set_ylabel("Average positive price (S$/kWh)")
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    fig.text(
        0.01, 0.01,
        "Source: LTA DataMall EV Charging Points Batch",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(
        OUTPUT_DIR / "ev_operator_price_vs_network.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"Operators visualised: {len(df)}")
    print(f"Charts saved to: {OUTPUT_DIR}")
    for filename in [
        "ev_operator_average_price.png",
        "ev_operator_network_size.png",
        "ev_operator_price_vs_network.png",
    ]:
        print(f"  - {filename}")


if __name__ == "__main__":
    main()
