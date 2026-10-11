from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "sg-ev-510713"
TABLE_ID = f"{PROJECT_ID}.ev_analytics.ev_operator_region_analysis"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            region,
            operator,
            charging_points,
            regional_share_pct,
            points_with_positive_price,
            avg_price_per_kwh
        FROM `{TABLE_ID}`
    """
    df = client.query(query).to_dataframe()

    if df.empty:
        raise ValueError("Regional analysis table contains no rows.")

    # Consistent region order for all charts
    region_order = ["Central", "East", "North", "North-East", "West"]
    df["region"] = pd.Categorical(
        df["region"], categories=region_order, ordered=True
    )

    # 1. Network coverage: top 5 operators per region
    coverage = (
        df.sort_values("charging_points", ascending=False)
        .groupby("region", observed=True)
        .head(5)
    )

    pivot = coverage.pivot_table(
        index="region",
        columns="operator",
        values="charging_points",
        aggfunc="sum",
        observed=True,
    ).fillna(0)

    ax = pivot.plot(
        kind="bar",
        stacked=True,
        figsize=(13, 7),
        width=0.78,
    )
    ax.set_title("EV Charging Network Coverage by Region")
    ax.set_xlabel("Region")
    ax.set_ylabel("Charging-point IDs")
    ax.legend(
        title="Operator",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
    )
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "ev_operator_region_coverage.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()

    # 2. Pricing heatmap
    price_pivot = df.pivot_table(
        index="operator",
        columns="region",
        values="avg_price_per_kwh",
        aggfunc="mean",
        observed=True,
    )

    # Order operators by their overall mean price
    price_pivot = price_pivot.loc[
        price_pivot.mean(axis=1).sort_values().index
    ]

    fig, ax = plt.subplots(figsize=(10, max(7, len(price_pivot) * 0.35)))
    image = ax.imshow(
        price_pivot.to_numpy(),
        aspect="auto",
        interpolation="nearest",
    )
    ax.set_xticks(range(len(price_pivot.columns)))
    ax.set_xticklabels(price_pivot.columns)
    ax.set_yticks(range(len(price_pivot.index)))
    ax.set_yticklabels(
        [
            name.replace(" PTE. LTD.", "").replace(
                " PRIVATE LIMITED", ""
            )
            for name in price_pivot.index
        ],
        fontsize=8,
    )

    for i in range(len(price_pivot.index)):
        for j in range(len(price_pivot.columns)):
            value = price_pivot.iloc[i, j]
            if pd.notna(value):
                ax.text(
                    j, i, f"{value:.3f}",
                    ha="center", va="center", fontsize=7,
                )

    fig.colorbar(image, ax=ax, label="Average price (S$/kWh)")
    ax.set_title("EV Charging Prices by Operator and Region")
    ax.set_xlabel("Region")
    ax.set_ylabel("Operator")
    fig.tight_layout()
    fig.savefig(
        OUTPUT_DIR / "ev_operator_region_pricing.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)

    # 3. Top-three operator concentration in each region
    top3 = (
        df.sort_values("charging_points", ascending=False)
        .groupby("region", observed=True)
        .head(3)
    )

    fig, ax = plt.subplots(figsize=(12, 7))
    for region in region_order:
        region_data = top3[top3["region"] == region].sort_values(
            "regional_share_pct", ascending=False
        )
        if not region_data.empty:
            ax.bar(
                [region] * len(region_data),
                region_data["regional_share_pct"],
                label=region,
            )

    # Use a direct horizontal chart for operator-level concentration instead
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 8))
    top3 = top3.copy()
    top3["region_operator"] = (
        top3["region"].astype(str)
        + " — "
        + top3["operator"].str.replace(" PTE. LTD.", "", regex=False)
        .str.replace(" PRIVATE LIMITED", "", regex=False)
    )
    top3 = top3.sort_values("regional_share_pct", ascending=True)

    bars = ax.barh(
        top3["region_operator"],
        top3["regional_share_pct"],
    )
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax.set_title("Top Three Operators by Regional Market Share")
    ax.set_xlabel("Share of kWh-priced charging-point IDs (%)")
    ax.set_ylabel("Region and operator")
    ax.set_xlim(0, 60)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(
        OUTPUT_DIR / "ev_operator_region_market_share.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"Regional rows visualised: {len(df)}")
    print(f"Charts saved to: {OUTPUT_DIR}")
    for name in (
        "ev_operator_region_coverage.png",
        "ev_operator_region_pricing.png",
        "ev_operator_region_market_share.png",
    ):
        print(f"  - {name}")


if __name__ == "__main__":
    main()

