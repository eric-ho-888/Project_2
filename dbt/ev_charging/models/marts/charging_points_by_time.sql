{{ config(
    materialized='table'
) }}

SELECT
    DATE(ingestion_timestamp) AS ingestion_date,
    TIMESTAMP_TRUNC(ingestion_timestamp, HOUR) AS ingestion_hour,
    COUNT(DISTINCT ev_cp_id) AS number_of_charging_points,
    COUNT(DISTINCT station_name) AS number_of_stations,
    COUNT(DISTINCT operator) AS number_of_operators
FROM {{ ref('stg_ev_charging') }}
GROUP BY
    ingestion_date,
    ingestion_hour
ORDER BY
    ingestion_date,
    ingestion_hour