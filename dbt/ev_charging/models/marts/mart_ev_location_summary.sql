{{ config(
    materialized='table',
    schema='ev_analytics'
) }}

SELECT
    postal_code,

    COUNT(DISTINCT ev_cp_id) AS charging_points,

    COUNT(DISTINCT station_name) AS stations,

    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL
  AND postal_code IS NOT NULL

GROUP BY postal_code

ORDER BY charging_points DESC