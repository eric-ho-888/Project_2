import os
import subprocess
import sys

PROJECT_ROOT = "/opt/sg-ev"
DBT_PROJECT = f"{PROJECT_ROOT}/dbt/sg_ev"
DBT_PROFILES = "/opt/dbt-profiles"

def run_pipeline():
    print("=== Step 1: LTA EV batch ingestion ===", flush=True)
    subprocess.run(
        [sys.executable, f"{PROJECT_ROOT}/ingestion/lta_ev_batch.py"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    print("=== Step 2: dbt build and tests ===", flush=True)
    subprocess.run(
        [
            "dbt",
            "build",
            "--project-dir", DBT_PROJECT,
            "--profiles-dir", DBT_PROFILES,
            "--target", "prod",
        ],
        cwd=DBT_PROJECT,
        check=True,
    )

    print("=== Pipeline completed successfully ===", flush=True)

if __name__ == "__main__":
    run_pipeline()
