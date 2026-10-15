
{{ config(materialized='view') }}

with strong_matches as (
    select
        carpark_id,
        count(distinct ev_cp_id) as strong_candidate_charging_points
    from {{ ref('bridge_ev_carpark') }}
    where match_status = 'strong_candidate'
    group by carpark_id
),

nearby_matches as (
    select
        carpark_id,
        count(distinct ev_cp_id) as nearby_charging_points,
        round(min(distance_meters), 2) as nearest_charger_distance_m
    from {{ ref('bridge_ev_carpark') }}
    group by carpark_id
)

select
    -- Preserve all existing HDB and planning-area fields
    c.*,

    -- Existing charger evidence
    coalesce(s.strong_candidate_charging_points, 0)
        as strong_candidate_charging_points,

    coalesce(n.nearby_charging_points, 0)
        as nearby_charging_points,

    n.nearest_charger_distance_m,

    -- Planning-area charging pressure
    p.occupancy_pct as planning_area_occupancy_pct,
    p.not_available_pct as planning_area_not_available_pct,
    p.candidate_coverage_pct as planning_area_candidate_coverage_pct,

    -- Preliminary classification
    case
        when coalesce(s.strong_candidate_charging_points, 0) = 0
             and p.occupancy_pct >= 30
            then 'priority_for_review'

        when coalesce(s.strong_candidate_charging_points, 0) = 0
            then 'coverage_gap_review'

        else 'existing_strong_candidate'
    end as preliminary_status

from {{ ref('dim_carpark_planning_area') }} c

left join strong_matches s
    on c.carpark_id = s.carpark_id

left join nearby_matches n
    on c.carpark_id = n.carpark_id

left join {{ ref('planning_area_coverage_pressure') }} p
    on c.planning_area = p.planning_area
