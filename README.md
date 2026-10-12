# Project_2

Data engineering and analysis project covering fuel prices, vehicle registration trends, and EV charging infrastructure in Singapore, drawing on Kaggle datasets, the LTA DataMall API, a cloud-based (Cloud Scheduler job run) and a local (ad-hoc Docker Dagster job run) ELT pipeline.

## Folder structure

```
Project_2/
├── data_kaggle/      # Kaggle datasets
├── data_lta/         # LTA DataMall datasets
├── notebook/         # Jupyter notebooks for exploratory analysis
└── sg-ev/            # Cloud pipeline: ingestion, dbt, Dagster, docs
```

### `data_kaggle/`

CSV files sourced from Kaggle. Only **`asia_fuel_prices_detailed.csv`** is used for analysis; the remaining files are kept for reference but are not part of the current scope.

| File | Used in analysis? |
|---|---|
| `asia_fuel_prices_detailed.csv` | Yes |
| `asia_subsidy_tracker.csv` | No |
| `crude_oil_annual.csv` | No |
| `fuel_tax_comparison.csv` | No |
| `global_fuel_prices.csv` | No |
| `price_trend_monthly.csv` | No |

### `data_lta/`

CSV files sourced from the LTA (Land Transport Authority) API. All files in this folder are used in the analysis.

| File | Description |
|---|---|
| `Car_Regn_by_make_8_2026.csv` | Monthly Car registrations by make from 2016-01 to 2026-08 |
| `coe_results_10_2026.csv` | Certificate of Entitlement (COE) bidding results from 2010-01 to 2026-10 |
| `New_Cars_by_make_type_2025.csv` | Yearly New car registrations by make and type from 2015 to 2025 |

### `notebook/`

Jupyter notebooks for exploratory data analysis.

| Notebook | Description |
|---|---|
| `new_car_reg_make.ipynb` | Monthly car registration analysis by make |
| `world_fuel.ipynb` | Global/regional fuel price analysis |
| `ya_car_pop_make.ipynb` | Yearly car population analysis by make |
| `oldev_charging_analysis.ipynb` | *(legacy — superseded by the `sg-ev` pipeline below)* Not used|

### `sg-ev/`

The EV charging infrastructure pipeline: ingestion from LTA DataMall, transformation with dbt, orchestration with Dagster, and deployment via Cloud Run. See **[`sg-ev/README.md`](./sg-ev/README.md)** for full setup and usage details. Also see **[sg-ev/docs/architecture.md](./sg-ev/docs/architecture.md)** for architecture layout.

## Getting started

1. Clone this repository.
2. Install dependencies for the folder you're working in (`notebook/` for exploratory analysis, `sg-ev/` for the pipeline — see both its own README and architecture files).
3. Open notebooks in your VS Code to reproduce the analysis in Python 3.11 environment.
4. Remember to change your file path should you require to run the Python scripts in your VS Code.