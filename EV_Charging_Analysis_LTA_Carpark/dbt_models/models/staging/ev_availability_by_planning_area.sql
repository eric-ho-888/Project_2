
{{ config(materialized='view') }}

with ranked_matches as (
    select
        b.ev_cp_id,
        b.carpark_id,
        b.distance_meters,
        b.match_status,

        row_number() over (
            partition by b.ev_cp_id
            order by
                b.distance_meters,
                b.carpark_id
        ) as match_rank

    from {{ ref('bridge_ev_carpark') }} b

    where b.match_status = 'strong_candidate'
),

charger_locations as (
    select
        r.ev_cp_id,
        r.carpark_id,
        c.planning_area,
        c.region_name

    from ranked_matches r

    join {{ ref('dim_carpark_planning_area') }} c
        on r.carpark_id = c.carpark_id

    where r.match_rank = 1
),

status_counts as (
    select
        l.planning_area,
        l.region_name,
        f.ev_cp_id,

        count(*) as total_observations,

        countif(f.evcp_status = '0')
            as occupied_observations,

        countif(f.evcp_status = '1')
            as available_observations,

        countif(f.evcp_status = '')
            as not_available_observations,

        countif(
            f.evcp_status is null
            or f.evcp_status not in ('0', '1', '')
        ) as unknown_observations

    from {{ ref('fact_charger_status') }} f

    join charger_locations l
        on f.ev_cp_id = l.ev_cp_id

    group by
        l.planning_area,
        l.region_name,
        f.ev_cp_id
)

select
    planning_area,
    region_name,

    count(distinct ev_cp_id)
        as matched_charging_points,

    sum(total_observations)
        as total_observations,

    sum(occupied_observations)
        as occupied_observations,

    sum(available_observations)
        as available_observations,

    sum(not_available_observations)
        as not_available_observations,

    sum(unknown_observations)
        as unknown_observations,

    round(
        100 * safe_divide(
            sum(occupied_observations),
            sum(occupied_observations)
                + sum(available_observations)
        ),
        2
    ) as occupancy_pct,

    round(
        100 * safe_divide(
            sum(available_observations),
            sum(total_observations)
        ),
        2
    ) as availability_pct,

    round(
        100 * safe_divide(
            sum(not_available_observations),
            sum(total_observations)
        ),
        2
    ) as not_available_pct

from status_counts

group by
    planning_area,
    region_name
