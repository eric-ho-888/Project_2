# Project_2

Data engineering and analysis project covering fuel prices, vehicle registration trends, and EV charging infrastructure in Singapore. It draws on Kaggle datasets, the LTA DataMall API and HDB carpark, with a cloud-based ELT pipeline (Cloud Scheduler job run) and a local one (ad-hoc Docker Dagster job run).

## Folder structure

```
Project_2/
├── data_kaggle/                        # Kaggle datasets
├── data_lta/                           # LTA DataMall datasets
├── notebook/                           # Jupyter notebooks for exploratory analysis
├── sg-ev/                              # Cloud pipeline: ingestion, dbt, Dagster, docs
└── EV_Charging_Analysis_LTA_Carpark/   # LTA DataMall and HDB Carpark datasets
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
| `Car_Regn_by_make_8_2026.csv` | Monthly car registrations by make from 2016-01 to 2026-08 |
| `coe_results_10_2026.csv` | Certificate of Entitlement (COE) bidding results from 2010-01 to 2026-10 |
| `New_Cars_by_make_type_2025.csv` | Yearly new car registrations by make and type from 2015 to 2025 |

### `notebook/`

Jupyter notebooks for exploratory data analysis.

| Notebook | Description |
|---|---|
| `new_car_reg_make.ipynb` | Monthly car registration analysis by make |
| `world_fuel.ipynb` | Global/regional fuel price analysis |
| `ya_car_pop_make.ipynb` | Yearly car population analysis by make |
| `oldev_charging_analysis.ipynb` | *Legacy, not used.* Superseded by the `sg-ev` pipeline below |

### `sg-ev/`

The EV charging infrastructure pipeline: ingestion from LTA DataMall, transformation with dbt, orchestration with Dagster, and deployment via Cloud Run.

- Setup and usage: [`sg-ev/README.md`](./sg-ev/README.md)
- Architecture layout: [`sg-ev/docs/architecture.md`](./sg-ev/docs/architecture.md)
- Data visualization analysis on LTA/BigQuery data: [`sg-ev/analytics/README.md`](./sg-ev/analytics/README.md)

### `EV_Charging_Analysis_LTA_Carpark/`

LTA/HDB carpark analysis. See [`EV_Charging_Analysis_LTA_Carpark/README.md`](./EV_Charging_Analysis_LTA_Carpark/README.md).

### Getting Started

1. Clone this repository.
2. Install dependencies for the folder you're working in:
   - `notebook/` for exploratory analysis
   - `sg-ev/` for the pipeline
   - `EV_Charging_Analysis_LTA_Carpark/` for HDB carpark analysis

   See each folder's own README and architecture files.
3. Open notebooks in VS Code to reproduce the analysis in a Python 3.11 environment.
4. Change the file paths if you need to run the Python scripts in your own VS Code setup.
5. For the project, you may refer to the PowerPoint file "EV_Charging_Data_Platform_Presentation_Final_Version" for the project.