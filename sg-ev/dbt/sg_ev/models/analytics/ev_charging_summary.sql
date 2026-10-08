{{ config(
    materialized='table'
) }}

SELECT
    region,

    COUNT(DISTINCT ev_cp_id) AS number_of_charging_points,

    COUNT(DISTINCT station_name) AS number_of_stations,

    COUNT(DISTINCT operator) AS number_of_operators,

    COUNTIF(charger_status = 1) AS active_charging_points,

    COUNTIF(charger_status = 0) AS inactive_charging_points,

    COUNTIF(current_type = 'AC') AS ac_charging_points,

    COUNTIF(current_type = 'DC') AS dc_charging_points,

    ROUND(AVG(power_rating_kw), 2) AS average_power_rating_kw,

    ROUND(AVG(price), 3) AS average_price,

    COUNTIF(price IS NULL) AS charging_points_without_price

FROM {{ ref('fct_ev_charging_points') }}

GROUP BY region

ORDER BY number_of_charging_points DESC
