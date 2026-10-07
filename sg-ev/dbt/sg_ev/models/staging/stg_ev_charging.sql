{{ config(
    materialized='view',
    schema='ev_staging'
) }}

SELECT
    last_updated_time,
    address,
    station_name,
    longitude,
    latitude,
    postal_code,
    charger_status,
    operating_hours,
    operator,
    position,
    charging_point_name,
    plug_type,
    price,
    `current` AS current_type,
    power_rating_kw,
    price_type,
    ev_cp_id,
    ev_id_status,
    ingestion_timestamp
FROM {{ source('ev_raw', 'ev_charging_raw') }}