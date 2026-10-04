from dagster import ScheduleDefinition, define_asset_job, AssetSelection


ev_charging_job = define_asset_job(
    name="ev_charging_pipeline",
    selection=AssetSelection.all(),
)


ev_charging_schedule = ScheduleDefinition(
    name="ev_charging_every_15_minutes",
    cron_schedule="*/15 * * * *",
    job=ev_charging_job,
)