
import subprocess
import sys

from dagster import (
    Definitions,
    ScheduleDefinition,
    job,
    op,
)

PROJECT_ROOT = "/opt/sg-ev"
DBT_PROJECT = f"{PROJECT_ROOT}/dbt/sg_ev"
DBT_PROFILES = "/opt/dagster/.dbt"
ANALYTICS_SCRIPT = f"{PROJECT_ROOT}/analytics/ev_analysis.py"


@op
def ingest_lta_batch() -> bool:
    """Refresh the current LTA EV charging snapshot."""
    subprocess.run(
        [sys.executable, f"{PROJECT_ROOT}/ingestion/lta_ev_batch.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return True


@op
def run_dbt_build(ingestion_succeeded: bool) -> bool:
    """Run dbt models and tests after successful ingestion."""
    if not ingestion_succeeded:
        raise RuntimeError(
            "LTA ingestion did not succeed; stopping dbt build."
        )

    subprocess.run(
        [
            "dbt",
            "build",
            "--project-dir", DBT_PROJECT,
            "--profiles-dir", DBT_PROFILES,
            "--target", "dev",
        ],
        cwd=DBT_PROJECT,
        check=True,
    )
    return True


@op
def run_ev_analytics(dbt_succeeded: bool) -> bool:
    """Generate Pandas, Polars and Matplotlib analytics outputs."""
    if not dbt_succeeded:
        raise RuntimeError(
            "dbt build did not succeed; stopping analytics."
        )

    subprocess.run(
        [sys.executable, ANALYTICS_SCRIPT],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return True


@job
def ev_charging_pipeline():
    dbt_succeeded = run_dbt_build(ingest_lta_batch())
    run_ev_analytics(dbt_succeeded)


daily_ev_schedule = ScheduleDefinition(
    job=ev_charging_pipeline,
    cron_schedule="30 9 * * *",
    execution_timezone="Asia/Singapore",
)


defs = Definitions(
    jobs=[ev_charging_pipeline],
    schedules=[daily_ev_schedule],
)
