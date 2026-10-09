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


@op
def ingest_lta_batch():
    """Refresh the current LTA EV charging snapshot."""
    subprocess.run(
        [sys.executable, f"{PROJECT_ROOT}/ingestion/lta_ev_batch.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )


@op
def run_dbt_build():
    """Run dbt models and tests after successful ingestion."""
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


@job
def ev_charging_pipeline():
    ingest_lta_batch()
    run_dbt_build()


daily_ev_schedule = ScheduleDefinition(
    job=ev_charging_pipeline,
    cron_schedule="30 9 * * *",
    execution_timezone="Asia/Singapore",
)


defs = Definitions(
    jobs=[ev_charging_pipeline],
    schedules=[daily_ev_schedule],
)
