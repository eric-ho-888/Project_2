
{{ config(materialized='view') }}

select
    ev_cp_id,

    safe.parse_timestamp(
        '%Y-%m-%d %H:%M:%S',
        snapshot_time
    ) as snapshot_time,

    -- Preserve original STRING status values
    charger_status,
    evcp_status,

    -- Preserve existing price field
    safe_cast(price as float64) as price,

    -- Overall charger status
    case
        when charger_status = '0' then 'Occupied'
        when charger_status = '1' then 'Available'
        when charger_status = '100' then 'Not Available'
        when charger_status is null then 'Missing'
        else 'Unknown'
    end as charger_status_label,

    -- Individual charging-point status
    case
        when evcp_status = '0' then 'Occupied'
        when evcp_status = '1' then 'Available'
        when evcp_status = '' then 'Not Available'
        when evcp_status is null then 'Missing or Source Unavailable'
        else 'Unknown'
    end as evcp_status_label,

    -- Identify interpretable connector statuses
    case
        when evcp_status in ('0', '1')
             or evcp_status = ''
            then true
        else false
    end as evcp_status_interpretable

from {{ source('datamall', 'ev_charging_points') }}
