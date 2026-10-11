# Singapore EV Charging Point Analytics

## Overview

This module analyses Singapore EV charging point data collected from
LTA DataMall EV Charging Points Batch and stored in Google BigQuery.

## Technology stack

- Python 3.11
- Pandas: business metrics and CSV exports
- Polars: independent data aggregation and validation
- Matplotlib: presentation-ready visualisations
- Google BigQuery: analytics data source
- dbt: data transformation and analytics tables

## Data sources

Google Cloud project: sg-ev-510713
BigQuery dataset: ev_analytics

Tables:
- dim_ev_charger
- fct_ev_charging_points
- ev_charging_summary

## Run the analysis

Activate the Conda environment from the project root:

    conda activate sg-ev
    python analytics/ev_analysis.py

The script uses Google Cloud Application Default Credentials
to access BigQuery.

## Generated outputs

Files are written to analytics/outputs/.

- regional_connectors.png
- connector_status_by_region.png
- ac_dc_distribution.png
- operator_distribution.png
- power_rating_by_region.png
- analysis_results.csv
- regional_summary.csv
- operator_summary.csv
- power_rating_by_region.csv
- pandas_polars_validation.csv

## Data validation

The script independently aggregates connector counts using Pandas
and Polars. It compares the regional results and stops with an error
if the counts do not match.

## Interpretation

Charts describe the current ingested snapshot. They should not be
interpreted as historical trends without suitable historical data.

Historical snapshot collection continues unless manually paused, 
followed by both data refreshes and dbt transformations.

## Project structure

    analytics/
    ├── README.md
    ├── requirements.txt
    ├── ev_analysis.py
    └── outputs/
        ├── charts
        └── CSV reports
