{{ config(
    materialized='table'
) }}

WITH classified AS (

    SELECT
        ev_cp_id,
        station_name,
        address,
        latitude,
        longitude,
        operator,
        plug_type,
        power_rating_kw,
        price,

        CASE
            -- Central Singapore
            WHEN latitude BETWEEN 1.275 AND 1.335
                 AND longitude BETWEEN 103.780 AND 103.900
                THEN 'Central'

            -- East Singapore
            WHEN longitude >= 103.900
                THEN 'East'

            -- West Singapore
            WHEN longitude < 103.780
                THEN 'West'

            -- North Singapore
            WHEN latitude >= 1.335
                THEN 'North'

            -- South Singapore
            WHEN latitude < 1.275
                THEN 'South'

            ELSE 'Central'
        END AS region

    FROM {{ ref('charging_points_current') }}

)

SELECT
    region,
    COUNT(DISTINCT ev_cp_id) AS number_of_charging_points,
    COUNT(DISTINCT station_name) AS number_of_stations,
    COUNT(DISTINCT operator) AS number_of_operators,
    ROUND(AVG(power_rating_kw), 2) AS avg_power_rating_kw,
    ROUND(AVG(price), 4) AS avg_price

FROM classified

GROUP BY region

ORDER BY number_of_charging_points DESC