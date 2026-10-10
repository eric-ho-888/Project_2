
{{ config(materialized='table') }}

SELECT
    ev_cp_id,
    station_name,
    address,
    postal_code,
    latitude,
    longitude,
    operator,
    charging_point_name,
    plug_type,
    current_type,
    power_rating_kw,
    operating_hours,
    position
FROM {{ ref('stg_ev_charging') }}
