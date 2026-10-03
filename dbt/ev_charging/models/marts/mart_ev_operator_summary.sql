{{ config(
    materialized='table',
    schema='ev_analytics'
) }}

SELECT
    operator,
    COUNT(DISTINCT ev_cp_id) AS charging_points,
    COUNT(DISTINCT station_name) AS stations,
    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw,
    ROUND(AVG(price), 2) AS avg_price

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL
  AND operator IS NOT NULL

GROUP BY operator

ORDER BY charging_points DESC