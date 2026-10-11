from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.chart import ScatterChart, Series, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.utils import get_column_letter

PROJECT = "sg-ev-510713"
TABLE_ID = f"{PROJECT}.ev_analytics.ev_operator_region_analysis"
WORKBOOK = (
    Path(__file__).resolve().parent
    / "outputs"
    / "ev_operator_region_analysis.xlsx"
)

REGIONS = ["Central", "East", "North", "North-East", "West"]
COLORS = {
    "Central": "4472C4",
    "East": "ED7D31",
    "North": "70AD47",
    "North-East": "A5A5A5",
    "West": "8064A2",
}
NAVY = "17365D"
TEAL = "0F6B78"


def style_title(ws, heading, subtitle, last_col):
    ws.merge_cells(
        start_row=1, start_column=1,
        end_row=1, end_column=last_col
    )
    c = ws.cell(1, 1, heading)
    c.font = Font(name="Aptos Display", size=18, bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor=NAVY)
    c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 38

    ws.merge_cells(
        start_row=2, start_column=1,
        end_row=2, end_column=last_col
    )
    c = ws.cell(2, 1, subtitle)
    c.font = Font(size=10, italic=True, color="667085")
    c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 32


def write_data(ws, df):
    header_row = 4

    for col, name in enumerate(df.columns, 1):
        c = ws.cell(header_row, col, str(name))
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=TEAL)
        c.alignment = Alignment(wrap_text=True, vertical="center")

    for row, values in enumerate(
        df.itertuples(index=False, name=None), header_row + 1
    ):
        for col, value in enumerate(values, 1):
            if pd.isna(value):
                value = None
            elif hasattr(value, "item"):
                value = value.item()

            c = ws.cell(row, col, value)
            if row % 2 == 0:
                c.fill = PatternFill("solid", fgColor="F3F6FA")

    if len(df):
        ws.auto_filter.ref = (
            f"A4:{get_column_letter(len(df.columns))}{4 + len(df)}"
        )
    ws.freeze_panes = "A5"

    for col, name in enumerate(df.columns, 1):
        values = [len(str(name))]
        values.extend(
            len(str(v)) for v in df.iloc[:, col - 1].dropna().tolist()
        )
        ws.column_dimensions[get_column_letter(col)].width = min(
            max(max(values) + 2, 14), 34
        )


def build_chart(data_ws, region_rows, title, width=16, height=9):
    chart = ScatterChart()
    chart.title = title
    chart.style = 13
    chart.scatterStyle = "marker"
    chart.x_axis.title = "Regional market share (%)"
    chart.y_axis.title = "Average price (S$/kWh)"
    chart.x_axis.numFmt = '0.0"%"'
    chart.y_axis.numFmt = '"$"0.00'
    chart.x_axis.scaling.min = 0
    chart.y_axis.scaling.min = 0
    chart.width = width
    chart.height = height
    chart.legend = None

    # Exactly one standard scatter series for the selected region.
    first_row, last_row, region = region_rows
    x_values = Reference(
        data_ws, min_col=3, min_row=first_row, max_row=last_row
    )
    y_values = Reference(
        data_ws, min_col=4, min_row=first_row, max_row=last_row
    )

    series = Series(y_values, x_values)
    series.tx = SeriesLabel(v=region)
    series.marker.symbol = "circle"
    series.marker.size = 8
    color = COLORS.get(region, "4472C4")
    series.graphicalProperties.solidFill = color
    series.graphicalProperties.line.noFill = True
    chart.series.append(series)

    return chart


def main():
    if not WORKBOOK.exists():
        raise FileNotFoundError(
            f"Workbook not found: {WORKBOOK}. "
            "Run analytics/export_ev_operator_region_excel.py first."
        )

    client = bigquery.Client(project=PROJECT)
    sql = f"""
        SELECT
            region,
            operator,
            regional_share_pct,
            avg_price_per_kwh,
            charging_points,
            points_with_positive_price
        FROM `{TABLE_ID}`
        WHERE regional_share_pct IS NOT NULL
          AND avg_price_per_kwh IS NOT NULL
          AND avg_price_per_kwh > 0
        ORDER BY region, regional_share_pct DESC
    """
    df = client.query(sql).to_dataframe()

    if df.empty:
        raise ValueError("No records have both market share and price.")

    df["region"] = df["region"].fillna("Unknown").astype(str)
    df["operator"] = df["operator"].fillna("Unknown operator").astype(str)

    numeric = [
        "regional_share_pct", "avg_price_per_kwh",
        "charging_points", "points_with_positive_price"
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=["regional_share_pct", "avg_price_per_kwh"]
    ).reset_index(drop=True)

    wb = load_workbook(WORKBOOK)

    # Remove previous versions of these two sheets so reruns are safe.
    for name in ["Scatter Data", "Regional Scatter Plots"]:
        if name in wb.sheetnames:
            del wb[name]

    data_ws = wb.create_sheet("Scatter Data")
    data_ws.sheet_view.showGridLines = False
    style_title(
        data_ws,
        "Market Share vs Price — Supporting Data",
        "Each row represents one operator in one region. Market share is "
        "based on kWh-priced records; price is the average positive S$/kWh.",
        len(df.columns),
    )
    write_data(data_ws, df)

    headers = {
        data_ws.cell(4, col).value: col
        for col in range(1, len(df.columns) + 1)
    }
    for row in range(5, 5 + len(df)):
        data_ws.cell(
            row, headers["regional_share_pct"]
        ).number_format = '0.00"%"'
        data_ws.cell(
            row, headers["avg_price_per_kwh"]
        ).number_format = '"$"#,##0.000'
        for col_name in ["charging_points", "points_with_positive_price"]:
            data_ws.cell(row, headers[col_name]).number_format = "#,##0"

    # Determine each region's contiguous data-row range.
    region_ranges = {}
    for region in REGIONS:
        indexes = df.index[df["region"] == region].tolist()
        if indexes:
            region_ranges[region] = (
                indexes[0] + 5,
                indexes[-1] + 5,
                region,
            )

    # Combined plot: five series, one per region.
    dashboard = wb["Dashboard"]
    dashboard.sheet_view.showGridLines = False
    combined = ScatterChart()
    combined.title = "Market Share vs Average Price — All Regions"
    combined.style = 13
    combined.scatterStyle = "marker"
    combined.x_axis.title = "Regional market share (%)"
    combined.y_axis.title = "Average price (S$/kWh)"
    combined.x_axis.numFmt = '0.0"%"'
    combined.y_axis.numFmt = '"$"0.00'
    combined.x_axis.scaling.min = 0
    combined.y_axis.scaling.min = 0
    combined.width = 24
    combined.height = 14
    combined.legend.position = "b"

    for region, (first_row, last_row, _) in region_ranges.items():
        x_values = Reference(
            data_ws, min_col=3, min_row=first_row, max_row=last_row
        )
        y_values = Reference(
            data_ws, min_col=4, min_row=first_row, max_row=last_row
        )
        series = Series(y_values, x_values)
        series.tx = SeriesLabel(v=region)
        series.marker.symbol = "circle"
        series.marker.size = 8
        color = COLORS[region]
        series.graphicalProperties.solidFill = color
        series.graphicalProperties.line.noFill = True
        combined.series.append(series)

    # Keep the original three charts; position the scatter below them.
    dashboard.add_chart(combined, "A53")

    # Five separate regional plots, arranged vertically for readable size.
    regional_ws = wb.create_sheet("Regional Scatter Plots")
    regional_ws.sheet_view.showGridLines = False
    style_title(
        regional_ws,
        "Regional Market Share vs Price",
        "Each dot is an operator. Compare the horizontal position "
        "(market share) with the vertical position (average price).",
        10,
    )

    positions = {
        "Central": "A4",
        "East": "J4",
        "North": "A24",
        "North-East": "J24",
        "West": "A44",
    }
    for region, rows in region_ranges.items():
        chart = build_chart(
            data_ws,
            rows,
            f"{region}: Market Share vs Average Price",
        )
        regional_ws.add_chart(chart, positions[region])

    # Region colour key.
    regional_ws["S4"] = "Region colour key"
    regional_ws["S4"].font = Font(bold=True)
    for i, region in enumerate(REGIONS, 5):
        cell = regional_ws.cell(i, 19, region)
        cell.fill = PatternFill("solid", fgColor=COLORS[region])
        cell.font = Font(bold=True, color="FFFFFF")
    regional_ws.column_dimensions["S"].width = 20

    dashboard.sheet_properties.tabColor = NAVY
    data_ws.sheet_properties.tabColor = TEAL
    regional_ws.sheet_properties.tabColor = "8064A2"

    # Save and reopen to verify the workbook structure.
    wb.save(WORKBOOK)
    check = load_workbook(WORKBOOK)

    print(f"Updated workbook: {WORKBOOK}")
    print(f"Scatter data points: {len(df)}")
    print(f"Combined dashboard charts: {len(check['Dashboard']._charts)}")
    print(
        "Regional charts:",
        len(check["Regional Scatter Plots"]._charts),
    )
    print("Workbook reopened successfully.")


if __name__ == "__main__":
    main()
