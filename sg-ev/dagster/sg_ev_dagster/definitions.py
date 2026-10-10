
import os
import subprocess
import sys
from pathlib import Path

from dagster import Definitions, job, op


# Resolve the project root from this file's location.
# Local: /home/eric/NTU_DSAI/Project_2/sg-ev
# Docker: /opt/sg-ev
PROJECT_ROOT = Path(
    os.environ.get(
        "SG_EV_PROJECT_ROOT",
        str(Path(__file__).resolve().parents[2]),
    )
).resolve()

DBT_PROJECT = PROJECT_ROOT / "dbt" / "sg_ev"

# Local default: ~/.dbt
# Docker can override this with DBT_PROFILES_DIR=/opt/dagster/.dbt
DBT_PROFILES = Path(
    os.environ.get(
        "DBT_PROFILES_DIR",
        str(Path.home() / ".dbt"),
    )
).expanduser()

ANALYTICS_SCRIPT = PROJECT_ROOT / "analytics" / "ev_analysis.py"
INGESTION_SCRIPT = PROJECT_ROOT / "ingestion" / "lta_ev_batch.py"


@op
def ingest_lta_batch() -> bool:
    """Refresh the current LTA EV charging snapshot."""
    subprocess.run(
        [sys.executable, str(INGESTION_SCRIPT)],
        cwd=str(PROJECT_ROOT),
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
            "--project-dir", str(DBT_PROJECT),
            "--profiles-dir", str(DBT_PROFILES),
            "--target", "dev",
        ],
        cwd=str(DBT_PROJECT),
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
        [sys.executable, str(ANALYTICS_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        check=True,
    )

    return True

@job
def ev_charging_pipeline():
    dbt_succeeded = run_dbt_build(ingest_lta_batch())
    run_ev_analytics(dbt_succeeded)


# Manual execution only. Cloud Scheduler owns production scheduling.
defs = Definitions(
    jobs=[ev_charging_pipeline],
    schedules=[],
)
