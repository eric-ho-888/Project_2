from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter

PROJECT = "sg-ev-510713"
TABLE_ID = f"{PROJECT}.ev_analytics.ev_operator_region_analysis"
OUT = Path(__file__).resolve().parent / "outputs" / "ev_operator_region_analysis.xlsx"

REGIONS = ["Central", "East", "North", "North-East", "West"]
NAVY = "17365D"
TEAL = "0F6B78"
PALE = "F3F6FA"
WHITE = "FFFFFF"
BLUE = "4472C4"
GREEN = "70AD47"
GREY = "667085"


def make_title(ws, heading, subtitle, last_col):
    ws.merge_cells(
        start_row=1, start_column=1,
        end_row=1, end_column=last_col
    )
    cell = ws.cell(1, 1, heading)
    cell.font = Font(name="Aptos Display", size=19, bold=True, color=WHITE)
    cell.fill = PatternFill("solid", fgColor=NAVY)
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 38

    ws.merge_cells(
        start_row=2, start_column=1,
        end_row=2, end_column=last_col
    )
    cell = ws.cell(2, 1, subtitle)
    cell.font = Font(name="Aptos", size=10, italic=True, color=GREY)
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 32


def write_df(ws, df, start_row=4):
    """Write formatted worksheet data without embedded Excel Table objects."""
    for col, name in enumerate(df.columns, 1):
        cell = ws.cell(start_row, col, str(name))
        cell.font = Font(bold=True, color=WHITE, size=10)
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

    for row_num, values in enumerate(
        df.itertuples(index=False, name=None), start_row + 1
    ):
        for col, value in enumerate(values, 1):
            if pd.isna(value):
                value = None
            elif hasattr(value, "item"):
                value = value.item()

            cell = ws.cell(row_num, col, value)
            cell.font = Font(name="Aptos", size=10, color="243247")
            if row_num % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=PALE)

    last_col = get_column_letter(max(1, len(df.columns)))
    last_row = start_row + len(df)
    ws.freeze_panes = f"A{start_row + 1}"
    if len(df.columns) and len(df):
        ws.auto_filter.ref = f"A{start_row}:{last_col}{last_row}"
    ws.row_dimensions[start_row].height = 34
    return last_row


def fit_columns(ws, max_width=34):
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        values = [
            len(str(ws.cell(row, col_idx).value))
            for row in range(1, ws.max_row + 1)
            if ws.cell(row, col_idx).value is not None
        ]
        width = max(values, default=10) + 2
        ws.column_dimensions[letter].width = min(max(width, 12), max_width)


def make_bar_chart(ws, title, x_title, y_title, data_col, category_col,
                   first_row, last_row, anchor, width=17, height=10):
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = title
    chart.x_axis.title = x_title
    chart.y_axis.title = y_title
    chart.height = height
    chart.width = width
    chart.legend = None
    chart.varyColors = False
    chart.gapWidth = 55

    data = Reference(
        ws, min_col=data_col, max_col=data_col,
        min_row=first_row - 1, max_row=last_row
    )
    cats = Reference(
        ws, min_col=category_col, max_col=category_col,
        min_row=first_row, max_row=last_row
    )
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True
    chart.dataLabels.position = "outEnd"
    ws.parent["Dashboard"].add_chart(chart, anchor)
    return chart


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    client = bigquery.Client(project=PROJECT)
    sql = f"""
        SELECT
            region, operator, charging_points, regional_share_pct,
            points_with_positive_price, avg_price_per_kwh,
            min_price_per_kwh, max_price_per_kwh
        FROM `{TABLE_ID}`
        ORDER BY region, charging_points DESC
    """
    df = client.query(sql).to_dataframe()

    if df.empty:
        raise ValueError(f"No rows found in {TABLE_ID}")

    df["region"] = df["region"].fillna("Unknown").astype(str)
    df["operator"] = df["operator"].fillna("Unknown operator").astype(str)

    numeric_cols = [
        "charging_points", "regional_share_pct", "points_with_positive_price",
        "avg_price_per_kwh", "min_price_per_kwh", "max_price_per_kwh"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    regions = [r for r in REGIONS if r in df["region"].unique()]
    regions += [r for r in sorted(df["region"].unique()) if r not in regions]

    # Detailed coverage pivot: all operators across all regions.
    coverage = (
        df.pivot_table(
            index="region", columns="operator",
            values="charging_points", aggfunc="sum", fill_value=0
        )
        .reindex(regions).fillna(0).reset_index()
    )
    coverage.columns.name = None

    # Pricing by operator and region.
    pricing = (
        df.pivot_table(
            index="operator", columns="region",
            values="avg_price_per_kwh", aggfunc="mean"
        )
        .reindex(columns=regions).reset_index()
    )
    pricing.columns.name = None

    # Rank operators by summed operator-region counts.
    operator_summary = (
        df.groupby("operator", as_index=False)["charging_points"]
        .sum()
        .sort_values("charging_points", ascending=False)
    )
    top10 = operator_summary.head(10).sort_values("charging_points")
    top10 = top10.rename(
        columns={"operator": "Operator", "charging_points": "Operator-region count"}
    )

    # Top 3 operators by count in each region, for regional share detail.
    top3 = (
        df.sort_values("charging_points", ascending=False)
        .groupby("region", group_keys=False)
        .head(3)
        .copy()
    )
    top3["Region — Operator"] = top3["region"] + " — " + top3["operator"]
    market = top3[
        ["Region — Operator", "regional_share_pct", "charging_points"]
    ].rename(columns={
        "regional_share_pct": "Regional share (%)",
        "charging_points": "Charging-point count"
    }).sort_values("Regional share (%)", ascending=True)

    # Keep the pricing chart to the eight largest operators for legibility.
    top8_names = operator_summary.head(8)["operator"].tolist()
    price_chart_data = (
        pricing[pricing["operator"].isin(top8_names)]
        .set_index("operator")
        .reindex(top8_names)
        .reset_index()
    )

    wb = Workbook()
    dashboard = wb.active
    dashboard.title = "Dashboard"
    coverage_ws = wb.create_sheet("Regional Coverage")
    pricing_ws = wb.create_sheet("Regional Pricing")
    market_ws = wb.create_sheet("Market Share")
    source_ws = wb.create_sheet("Source Data")
    top_ws = wb.create_sheet("Operator Summary")

    # Dashboard heading and KPI cards.
    dashboard.sheet_view.showGridLines = False
    make_title(
        dashboard,
        "Singapore EV Charging Network",
        "Operator coverage and public kWh pricing | Source: BigQuery ev_analytics",
        14,
    )

    metrics = [
        ("Operator-region records", len(df)),
        ("Operators", df["operator"].nunique()),
        ("Regions", df["region"].nunique()),
        ("Source table rows", len(df)),
    ]
    for i, (label, value) in enumerate(metrics):
        col = 1 + i * 3
        dashboard.merge_cells(
            start_row=4, start_column=col,
            end_row=4, end_column=col + 1
        )
        dashboard.merge_cells(
            start_row=5, start_column=col,
            end_row=6, end_column=col + 1
        )
        a = dashboard.cell(4, col, label)
        a.font = Font(bold=True, color=WHITE, size=10)
        a.fill = PatternFill("solid", fgColor=TEAL)
        a.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        b = dashboard.cell(5, col, value)
        b.font = Font(bold=True, size=20, color=NAVY)
        b.fill = PatternFill("solid", fgColor="D9EAF7")
        b.alignment = Alignment(horizontal="center", vertical="center")

    dashboard.merge_cells("A8:N9")
    dashboard["A8"] = (
        "Reading the data: counts are operator-region charging-point IDs, not "
        "individual plugs. Regional share is calculated from kWh-priced records. "
        "Summed counts across regions should not be interpreted as unique national points."
    )
    dashboard["A8"].font = Font(size=10, color="344054")
    dashboard["A8"].fill = PatternFill("solid", fgColor=PALE)
    dashboard["A8"].alignment = Alignment(wrap_text=True, vertical="center")

    # Detail sheets.
    make_title(
        coverage_ws, "Regional Charging Network Coverage",
        "All operators; counts are charging-point IDs by region and operator.",
        max(3, len(coverage.columns))
    )
    write_df(coverage_ws, coverage)
    for row in range(5, 5 + len(coverage)):
        for col in range(2, 2 + len(coverage.columns) - 1):
            coverage_ws.cell(row, col).number_format = "#,##0"

    make_title(
        pricing_ws, "Regional kWh Pricing",
        "Average positive S$/kWh. Blank cells mean no available price.",
        max(3, len(pricing.columns))
    )
    write_df(pricing_ws, pricing)
    for row in range(5, 5 + len(pricing)):
        for col in range(2, 2 + len(regions)):
            pricing_ws.cell(row, col).number_format = '"$"#,##0.000'
    if len(pricing) and len(regions):
        pricing_ws.conditional_formatting.add(
            f"B5:{get_column_letter(1 + len(regions))}{4 + len(pricing)}",
            ColorScaleRule(
                start_type="min", start_color="D9EAD3",
                mid_type="percentile", mid_value=50, mid_color="FFF2CC",
                end_type="max", end_color="F4CCCC"
            )
        )

    make_title(
        market_ws, "Top Three Operators by Region",
        "Regional share (%) and charging-point count for the three largest operators in each region.",
        3
    )
    write_df(market_ws, market)
    for row in range(5, 5 + len(market)):
        market_ws.cell(row, 2).number_format = '0.00"%"'
        market_ws.cell(row, 3).number_format = "#,##0"

    make_title(
        source_ws, "BigQuery Source Data",
        f"Source: {TABLE_ID}. Use the header filters to inspect records.",
        len(df.columns)
    )
    write_df(source_ws, df)
    source_headers = {
        cell.value: cell.column for cell in source_ws[4]
    }
    for row in range(5, 5 + len(df)):
        source_ws.cell(row, source_headers["regional_share_pct"]).number_format = '0.00"%"'
        for name in ["avg_price_per_kwh", "min_price_per_kwh", "max_price_per_kwh"]:
            source_ws.cell(row, source_headers[name]).number_format = '"$"#,##0.000'
        for name in ["charging_points", "points_with_positive_price"]:
            source_ws.cell(row, source_headers[name]).number_format = "#,##0"

    make_title(
        top_ws, "Largest Operators by Summed Operator-Region Count",
        "This ranking sums counts across region/operator groups; it is not a deduplicated national total.",
        2
    )
    write_df(top_ws, top10)
    for row in range(5, 5 + len(top10)):
        top_ws.cell(row, 2).number_format = "#,##0"

    # Chart 1: simple horizontal comparison of the ten largest operators.
    make_bar_chart(
        top_ws,
        "Top 10 Operators by Operator-Region Count",
        "Summed count", "Operator",
        data_col=2, category_col=1,
        first_row=5, last_row=4 + len(top10),
        anchor="A11", width=19, height=10
    )

    # Chart 2: prices by region for eight largest operators.
    chart = LineChart()
    chart.style = 13
    chart.title = "Average kWh Price by Region — Top 8 Operators"
    chart.y_axis.title = "Average price (S$/kWh)"
    chart.x_axis.title = "Operator"
    chart.height = 10
    chart.width = 20
    chart.y_axis.numFmt = '"$"0.00'
    chart.y_axis.scaling.min = 0
    data = Reference(
        pricing_ws, min_col=2, max_col=1 + len(regions),
        min_row=4, max_row=4 + len(pricing)
    )
    cats = Reference(
        pricing_ws, min_col=1, min_row=5, max_row=4 + len(pricing)
    )
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.legend.position = "b"
    chart.display_blanks = "gap"
    # Plot only the eight most represented operators, in a dedicated chart-data sheet.
    chart_data_ws = wb.create_sheet("Pricing Chart Data")
    write_df(chart_data_ws, price_chart_data, start_row=4)
    chart_data_ws.sheet_state = "hidden"
    chart_data = Reference(
        chart_data_ws, min_col=2, max_col=1 + len(regions),
        min_row=4, max_row=4 + len(price_chart_data)
    )
    chart_cats = Reference(
        chart_data_ws, min_col=1,
        min_row=5, max_row=4 + len(price_chart_data)
    )
    chart = LineChart()
    chart.style = 13
    chart.title = "Average kWh Price by Region — Top 8 Operators"
    chart.y_axis.title = "Average price (S$/kWh)"
    chart.x_axis.title = "Operator"
    chart.height = 10
    chart.width = 20
    chart.y_axis.numFmt = '"$"0.00'
    chart.y_axis.scaling.min = 0
    chart.add_data(chart_data, titles_from_data=True)
    chart.set_categories(chart_cats)
    chart.legend.position = "b"
    chart.display_blanks = "gap"
    dashboard.add_chart(chart, "G11")

    # Chart 3: regional shares for the top three operators in each region.
    make_bar_chart(
        market_ws,
        "Top Operators' Regional Share",
        "Regional share (%)", "Region — operator",
        data_col=2, category_col=1,
        first_row=5, last_row=4 + len(market),
        anchor="A28", width=23, height=13
    )
    # Correct number format for share labels on the chart.
    share_chart = dashboard._charts[-1]
    share_chart.x_axis.numFmt = '0"%"'

    # Consistent worksheet formatting; no embedded Excel Table objects.
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_setup.orientation = "landscape"
        ws.sheet_view.zoomScale = 90
        fit_columns(ws)

    for ws, color in [
        (dashboard, NAVY),
        (coverage_ws, BLUE),
        (pricing_ws, TEAL),
        (market_ws, GREEN),
        (source_ws, "A5A5A5"),
        (top_ws, BLUE),
    ]:
        ws.sheet_properties.tabColor = color

    for col in range(1, 15):
        dashboard.column_dimensions[get_column_letter(col)].width = 13
    dashboard.freeze_panes = "A4"

    wb.save(OUT)
    print(f"Workbook created: {OUT}")
    print(f"Source rows: {len(df)}")
    print(f"Operators: {df['operator'].nunique()}")
    print(f"Regions: {df['region'].nunique()}")
    print("Excel Table objects disabled; worksheet AutoFilters retained.")
    print("Sheets: Dashboard, Regional Coverage, Regional Pricing, Market Share, Source Data, Operator Summary")


if __name__ == "__main__":
    main()
