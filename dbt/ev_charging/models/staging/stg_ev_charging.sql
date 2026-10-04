{{ config(
    materialized='table'
) }}

SELECT
    last_updated_time,
    address,
    station_name,

    CAST(longitude AS FLOAT64) AS longitude,
    CAST(latitude AS FLOAT64) AS latitude,

    postal_code,

    CAST(charger_status AS INT64) AS charger_status,

    operating_hours,
    operator,
    position,
    charging_point_name,
    plug_type,

    CAST(price AS FLOAT64) AS price,

    `current` AS current_type,

    CAST(power_rating_kw AS FLOAT64) AS power_rating_kw,

    price_type,
    ev_cp_id,

    CAST(ev_id_status AS INT64) AS ev_id_status,

    ingestion_timestamp

FROM {{ source('ev_raw', 'ev_charging_raw') }}