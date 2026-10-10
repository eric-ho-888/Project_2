{{ config(
    materialized='table'
) }}

SELECT
    ev_cp_id,
    station_name,
    operator,
    address,
    postal_code,
    latitude,
    longitude,
    plug_type,
    current_type,
    power_rating_kw,
    price,
    price_type,
    charger_status,
    ev_id_status,
    operating_hours,

CASE
    -- Central Region
    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 1 AND 13
        THEN 'Central'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 20 AND 24
        THEN 'Central'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 28 AND 41
        THEN 'Central'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) IN (56, 57)
        THEN 'Central'

    -- East Region
    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 14 AND 19
        THEN 'East'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 42 AND 52
        THEN 'East'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) = 81
        THEN 'East'

    -- North-East Region
    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 53 AND 55
        THEN 'North-East'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) IN (79, 80, 82)
        THEN 'North-East'

    -- West Region
    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 58 AND 71
        THEN 'West'

    -- North Region
    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 25 AND 27
        THEN 'North'

    WHEN SAFE_CAST(SUBSTR(postal_code, 1, 2) AS INT64) BETWEEN 72 AND 78
        THEN 'North'

    ELSE 'Unknown'
END AS region,

    last_updated_time,
    ingestion_timestamp

FROM {{ ref('stg_ev_charging') }}

WHERE ev_cp_id IS NOT NULL