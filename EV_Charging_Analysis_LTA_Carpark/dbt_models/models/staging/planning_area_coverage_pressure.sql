
{{ config(materialized='view') }}

-- 1. Count all HDB carparks in each planning area
with carpark_summary as (
    select
        planning_area,
        region_name,

        count(distinct carpark_id) as total_carparks,

        countif(is_free_parking = true)
            as carparks_with_free_parking,

        countif(has_night_parking = true)
            as carparks_with_night_parking,

        countif(has_short_term_parking = true)
            as carparks_with_short_term_parking

    from {{ ref('dim_carpark_planning_area') }}

    group by planning_area, region_name
),

-- 2. Count carparks with strong HDB-EV candidates
strong_carparks as (
    select distinct
        carpark_id
    from {{ ref('bridge_ev_carpark') }}
    where match_status = 'strong_candidate'
),

coverage_summary as (
    select
        c.planning_area,

        count(distinct s.carpark_id)
            as carparks_with_strong_ev_candidates

    from {{ ref('dim_carpark_planning_area') }} c

    left join strong_carparks s
        on c.carpark_id = s.carpark_id

    group by c.planning_area
),

-- 3. Reuse our existing charging-pressure results
charging_pressure as (
    select *
    from {{ ref('ev_availability_by_planning_area') }}
)

-- 4. Combine coverage, parking conditions and pressure
select
    c.planning_area,
    c.region_name,

    c.total_carparks,

    coalesce(
        v.carparks_with_strong_ev_candidates, 0
    ) as carparks_with_strong_ev_candidates,

    c.total_carparks -
        coalesce(
            v.carparks_with_strong_ev_candidates, 0
        ) as carparks_without_strong_ev_candidates,

    round(
        100 * safe_divide(
            coalesce(v.carparks_with_strong_ev_candidates, 0),
            c.total_carparks
        ),
        2
    ) as candidate_coverage_pct,

    -- Parking convenience
    c.carparks_with_free_parking,
    c.carparks_with_night_parking,
    c.carparks_with_short_term_parking,

    -- Historical EV availability
    coalesce(p.matched_charging_points, 0)
        as matched_charging_points,

    p.occupancy_pct,
    p.availability_pct,
    p.not_available_pct,
    p.unknown_observations

from carpark_summary c

left join coverage_summary v
    on c.planning_area = v.planning_area

left join charging_pressure p
    on c.planning_area = p.planning_area
