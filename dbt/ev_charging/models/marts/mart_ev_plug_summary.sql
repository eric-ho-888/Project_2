{{ config(
    materialized='table',
    schema='ev_analytics'
) }}

SELECT
    plug_type,
    COUNT(DISTINCT ev_cp_id) AS charging_points,
    COUNT(DISTINCT station_name) AS stations,
    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL
  AND plug_type IS NOT NULL

GROUP BY plug_type

ORDER BY charging_points DESC