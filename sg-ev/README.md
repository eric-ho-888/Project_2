# Singapore EV Charging Analytics

An end-to-end data engineering and analytics project using Singapore's
LTA DataMall EV Charging Points Batch API, Google Cloud, BigQuery, dbt,
Dagster, Pandas, Polars, and Matplotlib.

## Project goals

- Ingest the latest Singapore EV charging-point batch from LTA DataMall.
- Store source data in BigQuery.
- Transform and test data using dbt.
- Build dimensional, fact, and regional summary models.
- Analyse connector availability, connector types, operators, pricing,
  power ratings, and regional distribution.
- Generate CSV summaries and Matplotlib charts.
- Automate production ingestion and dbt daily with Cloud Scheduler and
  Cloud Run.
- Support manual end-to-end development runs with Docker and Dagster.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the detailed
architecture diagram, data layers, component responsibilities, and
orchestration design.

```text
LTA DataMall EVCBatch
        |
        v
Python ingestion
        |
        v
BigQuery: ev_raw
        |
        v
dbt staging
        |
        v
BigQuery: ev_staging
        |
        v
dbt analytics/star models
        |
        v
BigQuery: ev_analytics
        |
        v
Pandas + Polars + Matplotlib
        |
        v
CSV reports and charts
```

## Technology stack

| Area | Technology |
|---|---|
| Source | LTA DataMall EV Charging Points Batch API |
| Ingestion | Python 3.11, Requests, Google Cloud BigQuery client |
| Data warehouse | Google BigQuery |
| Transformation and testing | dbt Core, dbt BigQuery, dbt-utils, dbt-expectations |
| Orchestration | Cloud Scheduler, Cloud Run, Dagster |
| Local orchestration environment | Docker Compose |
| Data analysis | Pandas and Polars |
| Visualisation | Matplotlib |

## GCP configuration

- Project ID: `sg-ev-510713`
- Region: `asia-southeast1`
- Raw dataset: `ev_raw`
- Staging dataset: `ev_staging`
- Analytics dataset: `ev_analytics`

The BigQuery datasets use the configured US location. Keep BigQuery dataset
locations consistent with the datasets and jobs used by this project.

## Repository layout

```text
sg-ev/
├── ingestion/
│   └── lta_ev_batch.py
├── dbt/
│   └── sg_ev/
│       ├── dbt_project.yml
│       ├── packages.yml
│       └── models/
│           ├── staging/
│           ├── star/
│           │   ├── dimensions/
│           │   └── facts/
│           └── analytics/
├── analytics/
│   ├── ev_analysis.py
│   ├── requirements.txt
│   └── outputs/
├── dagster/
│   ├── requirements.txt
│   └── sg_ev_dagster/
│       └── definitions.py
├── docs/
│   └── architecture.md
├── Dockerfile
├── compose.yaml
├── workspace.yaml
├── .env
└── README.md
```

## Prerequisites

- Docker Engine and Docker Compose
- Google Cloud CLI (`gcloud`)
- BigQuery CLI (`bq`), if running BigQuery CLI queries
- Miniconda with Python 3.11 for local Python development
- Access to GCP project `sg-ev-510713`
- An LTA DataMall API key

A Python virtual environment created with `venv` is not required. Use the
existing Conda environment for local Python tasks and Docker for the
Dagster environment.

## Configure secrets

Create or update `.env` in the project root:

```dotenv
LTA_API_KEY=replace_with_your_lta_api_key
```

Never commit the real API key or paste it into source files or documentation.
Ensure `.env` is ignored by Git:

```gitignore
.env
```

Production uses Google Secret Manager secret `lta-api-key`, supplied to
Cloud Run as the `LTA_API_KEY` environment variable.

## Local Dagster environment

From the project root:

```bash
cd /home/eric/NTU_DSAI/Project_2/sg-ev
docker compose up -d --build
docker compose ps
```

Open the Dagster UI:

<http://localhost:3000>

Launch `ev_charging_pipeline` manually. It runs these steps in order:

1. `ingest_lta_batch` — refresh the current LTA snapshot.
2. `run_dbt_build` — build dbt models and run configured tests.
3. `run_ev_analytics` — compute analytics, validate regional counts, and
   write CSV and chart outputs.

To run analytics directly inside the container:

```bash
docker compose exec user_code \
  python /opt/sg-ev/analytics/ev_analysis.py
```

To stop the local services:

```bash
docker compose down
```

**Scheduling rule:** Cloud Scheduler is the production scheduler. Keep
the Dagster schedule stopped/disabled to avoid duplicate scheduled runs.

## Run dbt locally

Activate the existing Conda environment, if applicable:

```bash
conda activate sg-ev
cd /home/eric/NTU_DSAI/Project_2/sg-ev/dbt/sg_ev
```

Install dbt packages and validate the connection:

```bash
dbt deps
dbt debug
dbt build
```

These commands require valid dbt profile settings and Google Cloud
credentials. The Docker Dagster environment uses the profiles directory
`/opt/dagster/.dbt`.

## Production schedule

The production Cloud Scheduler job is configured as follows:

| Setting | Value |
|---|---|
| Scheduler job | `sg-ev-daily-schedule` |
| Cloud Run Job | `sg-ev-pipeline` |
| Schedule | `30 9 * * *` |
| Time zone | `Asia/Singapore` |
| Region | `asia-southeast1` |
| Frequency | Daily at 09:30 Singapore time |

Inspect the scheduler:

```bash
gcloud scheduler jobs describe sg-ev-daily-schedule \
  --location=asia-southeast1 \
  --project=sg-ev-510713
```

Manually trigger a production run:

```bash
gcloud run jobs execute sg-ev-pipeline \
  --region=asia-southeast1 \
  --project=sg-ev-510713
```

List recent executions:

```bash
gcloud run jobs executions list \
  --job=sg-ev-pipeline \
  --region=asia-southeast1 \
  --project=sg-ev-510713
```

The production Cloud Run job runs ingestion and dbt. Analytics currently
runs as part of the local/manual Dagster workflow, not the production
Cloud Run job.

## BigQuery data layers

### Raw — `ev_raw`

- `ev_charging_raw`: current snapshot of connector records.
- `ev_charging_history`: temporary daily snapshot collection.

The ingestion script calls the LTA DataMall endpoint:

<https://datamall2.mytransport.sg/ltaodataservice/EVCBatch>

The API returns a batch download link. The script downloads the JSON
payload, flattens nested location and charging-point information, and
loads records into BigQuery.

### Staging — `ev_staging`

- `stg_ev_charging`: staging view over the raw source.
- The raw field `current` is exposed as `current_type`.

### Analytics — `ev_analytics`

- `dim_ev_charger`: descriptive charger and location attributes.
- `fct_ev_charging_points`: connector-level fact records.
- `ev_charging_summary`: regional aggregate metrics.

The regional categories currently used are Central, East, North,
North-East, and West.

## Analytics outputs

The script `analytics/ev_analysis.py` creates outputs under
`analytics/outputs/`, including:

| Output | Description |
|---|---|
| `analysis_results.csv` | KPI results |
| `regional_summary.csv` | Regional connector summary |
| `pandas_polars_validation.csv` | Comparison of Pandas and Polars regional counts |
| `operator_summary.csv` | Connector distribution by operator |
| `power_rating_by_region.csv` | Power-rating analysis by region |
| `regional_connectors.png` | Connectors by region |
| `connector_status_by_region.png` | Connector status by region |
| `ac_dc_distribution.png` | AC/DC distribution |
| `operator_distribution.png` | Distribution by operator |
| `power_rating_by_region.png` | Power rating by region |

Previously validated analytics covered 11,605 connector records across
the five configured regions, with Pandas and Polars regional counts
matching. Counts are snapshots and will change when new LTA data is loaded.

## Metric interpretation

- A charging point or connector is not necessarily equivalent to a
  station or site. One site can contain multiple connectors.
- Unknown connector status should remain separate from available and
  occupied statuses.
- `average_price_per_kwh` is a simple, unweighted average of non-null
  connector prices; it is not usage-weighted.
- Missing `price` or `price_type` alone does not prove that a connector
  was newly installed.
- Validate unmapped postal sectors before presenting regional totals.

## Temporary history-snapshot plan

The project plan is to append one history snapshot per Singapore calendar
day. You can manually stop appending new history snapshots while continuing to refresh the current
raw snapshot and run the production pipeline.

The ingestion guard prevents a new history snapshot when one already
exists for the same Singapore calendar day. It does not automatically
remove duplicates created before the guard was introduced.

## Troubleshooting

### Ingestion failure

- Verify that `LTA_API_KEY` is available locally or through Secret Manager.
- Confirm the `EVCBatch` API returns a valid download link.
- Check Cloud Run execution logs for download, parsing, schema, or BigQuery
  errors.
- Verify the Cloud Run service account has the required BigQuery permissions.

### dbt failure

- Run `dbt debug` with the correct project and profiles directory.
- Confirm the source table exists:
  `sg-ev-510713.ev_raw.ev_charging_raw`.
- Review the failing model or test output.

### Analytics failure

- Confirm the `ev_analytics` tables exist and have been refreshed.
- Confirm the environment includes Pandas, Polars, Matplotlib,
  `google-cloud-bigquery`, and `db-dtypes`.
- Verify BigQuery credentials and output-directory write permissions.

## Security

- Do not commit `.env`, API keys, or service-account credentials.
- Use Secret Manager for production secrets.
- Prefer service-account-based authentication over long-lived downloaded
  key files.
- Review logs and execution status after failed scheduled runs.

## Data source

Land Transport Authority (LTA) DataMall — EV Charging Points Batch API.
Follow the current DataMall terms and attribution requirements.
