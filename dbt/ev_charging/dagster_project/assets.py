from pathlib import Path

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from .lta_ingestion import lta_ev_charging_raw


DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=Path.home() / ".dbt",
)

dbt_project.prepare_if_dev()

dbt = DbtCliResource(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=Path.home() / ".dbt",
)


@dbt_assets(
    manifest=dbt_project.manifest_path,
)
def dbt_models(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
):
    yield from dbt.cli(
        ["build"],
        context=context,
    ).stream()