{{ config(
    materialized='view',
    schema='ev_staging'
) }}

SELECT
    CAST(ev_cp_id AS STRING) AS ev_cp_id,

    CAST(station_name AS STRING) AS station_name,

    CAST(address AS STRING) AS address,

    CAST(postal_code AS STRING) AS postal_code,

    SAFE_CAST(latitude AS FLOAT64) AS latitude,

    SAFE_CAST(longitude AS FLOAT64) AS longitude,

    CAST(operator AS STRING) AS operator,

    CAST(charging_point_name AS STRING) AS charging_point_name,

    CAST(plug_type AS STRING) AS plug_type,

    SAFE_CAST(power_rating_kw AS FLOAT64) AS power_rating_kw,

    CAST(`current` AS STRING) AS current_type,

    SAFE_CAST(price AS FLOAT64) AS price,

    CAST(price_type AS STRING) AS price_type,

    SAFE_CAST(charger_status AS INT64) AS charger_status,

    CAST(operating_hours AS STRING) AS operating_hours,

    CAST(position AS STRING) AS position,

    SAFE_CAST(last_updated_time AS TIMESTAMP) AS last_updated_time,

    SAFE_CAST(ev_id_status AS INT64) AS ev_id_status,

    SAFE_CAST(ingestion_timestamp AS TIMESTAMP) AS ingestion_timestamp

FROM {{ source('ev_raw', 'ev_charging_raw') }}