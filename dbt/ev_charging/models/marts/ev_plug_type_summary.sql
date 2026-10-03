{{ config(
    materialized='table',
    schema='ev_analytics'
) }}

SELECT
    plug_type,

    COUNT(DISTINCT ev_cp_id) AS charging_points,

    COUNT(DISTINCT station_name) AS stations,

    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw,

    ROUND(
        100 * COUNT(DISTINCT ev_cp_id)
        / SUM(COUNT(DISTINCT ev_cp_id)) OVER (),
        2
    ) AS percentage_of_charging_points

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL
  AND plug_type IS NOT NULL

GROUP BY plug_type

ORDER BY charging_points DESC