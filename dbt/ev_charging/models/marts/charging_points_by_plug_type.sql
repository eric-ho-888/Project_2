{{ config(
    materialized='table'
) }}

SELECT
    plug_type,
    COUNT(DISTINCT ev_cp_id) AS number_of_charging_points,
    COUNT(DISTINCT station_name) AS number_of_stations,
    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw,
    ROUND(AVG(price), 4) AS avg_price
FROM {{ ref('charging_points_current') }}
GROUP BY plug_type
ORDER BY number_of_charging_points DESC