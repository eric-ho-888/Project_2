{{ config(
    materialized='table',
    schema='ev_analytics'
) }}

SELECT
    ev_cp_id,
    station_name,
    charging_point_name,
    address,
    operator,
    latitude,
    longitude,
    plug_type,
    power_rating_kw,
    price,
    price_type,
    charger_status,
    operating_hours,
    position,
    last_updated_time,
    ev_id_status,
    ingestion_timestamp

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL