
{{ config(materialized='view') }}

with charger_locations as (
    select
        ev_cp_id,
        location_name,
        address,
        postal_code,

        -- Provisional physical-location grouping
        to_hex(sha256(to_json_string(struct(
            upper(trim(coalesce(location_name, ''))),
            upper(trim(coalesce(address, ''))),
            trim(coalesce(postal_code, ''))
        )))) as provisional_location_id

    from {{ ref('dim_charger') }}
),

expected_connectors as (
    select
        provisional_location_id,
        count(distinct ev_cp_id) as expected_connectors
    from charger_locations
    group by provisional_location_id
),

connector_snapshots as (
    select
        l.provisional_location_id,
        f.ev_cp_id,
        f.snapshot_time,
        f.evcp_status,

        -- One observation per connector per timestamp
        row_number() over (
            partition by f.ev_cp_id, f.snapshot_time
            order by f.evcp_status
        ) as observation_rank

    from {{ ref('fact_charger_status') }} f

    join charger_locations l
        on f.ev_cp_id = l.ev_cp_id

    where f.snapshot_time is not null
),

location_snapshots as (
    select
        provisional_location_id,
        snapshot_time,

        count(distinct ev_cp_id) as observed_connectors,

        countif(evcp_status = '1') as available_connectors,
        countif(evcp_status = '0') as occupied_connectors,
        countif(evcp_status = '') as not_available_connectors,

        countif(
            evcp_status is null
            or evcp_status not in ('0', '1', '')
        ) as unknown_connectors

    from connector_snapshots
    where observation_rank = 1

    group by
        provisional_location_id,
        snapshot_time
),

classified_snapshots as (
    select
        s.*,
        e.expected_connectors,

        -- Require all expected connectors to be observed
        s.observed_connectors = e.expected_connectors
            and s.unknown_connectors = 0
            as is_complete_snapshot,

        -- No available connectors, with all observed occupied
        s.available_connectors = 0
            and s.occupied_connectors = e.expected_connectors
            as all_occupied,

        -- No available connectors, regardless of reason
        s.available_connectors = 0
            as zero_available

    from location_snapshots s

    join expected_connectors e
        using (provisional_location_id)
),

location_summary as (
    select
        provisional_location_id,

        count(*) as total_snapshots,

        countif(is_complete_snapshot)
            as complete_snapshots,

        countif(
            is_complete_snapshot and zero_available
        ) as zero_available_snapshots,

        countif(
            is_complete_snapshot and all_occupied
        ) as all_occupied_snapshots,

        round(
            100 * safe_divide(
                countif(
                    is_complete_snapshot and zero_available
                ),
                countif(is_complete_snapshot)
            ),
            2
        ) as zero_availability_pct,

        round(
            100 * safe_divide(
                countif(
                    is_complete_snapshot and all_occupied
                ),
                countif(is_complete_snapshot)
            ),
            2
        ) as all_occupied_pct

    from classified_snapshots
    group by provisional_location_id
)

select
    s.*,
    e.expected_connectors,

    round(
        100 * safe_divide(
            s.complete_snapshots,
            s.total_snapshots
        ),
        2
    ) as snapshot_completeness_pct

from location_summary s

join expected_connectors e
    using (provisional_location_id)
