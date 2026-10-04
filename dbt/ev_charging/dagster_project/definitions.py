from dagster import Definitions

from .assets import dbt_models, dbt
from .lta_ingestion import lta_ev_charging_raw
from .schedules import ev_charging_schedule


defs = Definitions(
    assets=[
        lta_ev_charging_raw,
        dbt_models,
    ],
    resources={
        "dbt": dbt,
    },
    schedules=[
        ev_charging_schedule,
    ],
)