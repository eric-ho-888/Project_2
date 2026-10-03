{{ config(
    materialized='table',
    schema='ev_analytics'
) }}

SELECT
    COUNT(DISTINCT ev_cp_id) AS total_charging_points,
    COUNT(DISTINCT station_name) AS total_stations,
    COUNT(DISTINCT operator) AS total_operators,
    COUNT(DISTINCT plug_type) AS total_plug_types,

    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw,

    COUNTIF(charger_status = 1) AS active_charging_points,
    COUNTIF(charger_status = 0) AS inactive_charging_points,

    ROUND(AVG(price), 2) AS avg_price

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL