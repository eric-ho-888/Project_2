from dagster import Definitions

from .assets import dbt_models, dbt


defs = Definitions(
    assets=[dbt_models],
    resources={
        "dbt": dbt,
    },
)