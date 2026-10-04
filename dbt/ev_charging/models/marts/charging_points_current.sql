{{ config(
    materialized='table'
) }}

SELECT *
FROM {{ ref('stg_ev_charging') }}

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ev_cp_id
    ORDER BY ingestion_timestamp DESC
) = 1