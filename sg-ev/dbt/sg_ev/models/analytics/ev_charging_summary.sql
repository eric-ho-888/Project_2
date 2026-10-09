
{{ config(materialized='table') }}

WITH base AS (
    SELECT *
    FROM {{ ref('fct_ev_charging_points') }}
),

station_level AS (
    SELECT
        region,
        COUNT(DISTINCT IF(
            charger_status = 0,
            CONCAT(
                COALESCE(operator, ''), '|',
                COALESCE(station_name, ''), '|',
                COALESCE(address, '')
            ),
            NULL
        )) AS stations_fully_occupied,

        COUNT(DISTINCT IF(
            charger_status = 1,
            CONCAT(
                COALESCE(operator, ''), '|',
                COALESCE(station_name, ''), '|',
                COALESCE(address, '')
            ),
            NULL
        )) AS stations_with_available_connectors,

        COUNT(DISTINCT IF(
            charger_status = 100,
            CONCAT(
                COALESCE(operator, ''), '|',
                COALESCE(station_name, ''), '|',
                COALESCE(address, '')
            ),
            NULL
        )) AS stations_not_available
    FROM base
    GROUP BY region
),

connector_level AS (
    SELECT
        region,
        COUNT(DISTINCT ev_cp_id) AS total_connectors,

        COUNT(DISTINCT IF(
            ev_id_status = 1, ev_cp_id, NULL
        )) AS available_connectors,

        COUNT(DISTINCT IF(
            ev_id_status = 0, ev_cp_id, NULL
        )) AS occupied_connectors,

        COUNT(DISTINCT IF(
            ev_id_status IS NULL, ev_cp_id, NULL
        )) AS connectors_with_unknown_status,

        COUNT(DISTINCT IF(
            current_type = 'AC', ev_cp_id, NULL
        )) AS ac_connectors,

        COUNT(DISTINCT IF(
            current_type = 'DC', ev_cp_id, NULL
        )) AS dc_connectors,

        ROUND(
            AVG(IF(price_type = 'kWh', price, NULL)), 3
        ) AS average_price_per_kwh,

        ROUND(AVG(power_rating_kw), 2)
            AS average_power_rating_kw,

        COUNT(DISTINCT IF(
            price IS NULL OR price_type IS NULL,
            ev_cp_id, NULL
        )) AS connectors_with_incomplete_pricing

    FROM base
    GROUP BY region
)

SELECT
    c.*,
    s.stations_fully_occupied,
    s.stations_with_available_connectors,
    s.stations_not_available
FROM connector_level c
LEFT JOIN station_level s USING (region)