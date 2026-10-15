
{{ config(materialized='view') }}

with charger_locations as (
    select
        ev_cp_id,
        location_name,
        address,
        postal_code,
        latitude,
        longitude,
        coordinate_review_required,

        -- Must match the location-ID logic in
        -- ev_location_zero_availability.sql
        to_hex(sha256(to_json_string(struct(
            upper(trim(coalesce(location_name, ''))),
            upper(trim(coalesce(address, ''))),
            trim(coalesce(postal_code, ''))
        )))) as provisional_location_id

    from {{ ref('dim_charger') }}
),

location_coordinates as (
    select
        provisional_location_id,

        count(distinct ev_cp_id) as assigned_connectors,

        avg(
            if(not coordinate_review_required, latitude, null)
        ) as latitude,

        avg(
            if(not coordinate_review_required, longitude, null)
        ) as longitude,

        countif(coordinate_review_required)
            as connectors_requiring_coordinate_review

    from charger_locations
    group by provisional_location_id
),

planning_areas as (
    select
        PLN_AREA_N as planning_area,
        REGION_N as region_name,
        st_geogfromtext(geometry_wkt) as planning_geometry

    from {{ source('datamall', 'ura_planning_areas_2025') }}
),

location_planning_area as (
    select
        l.provisional_location_id,
        l.assigned_connectors,
        l.connectors_requiring_coordinate_review,
        p.planning_area,
        p.region_name

    from location_coordinates l

    left join planning_areas p
        on st_covers(
            p.planning_geometry,
            st_geogpoint(l.longitude, l.latitude)
        )

    where l.latitude is not null
      and l.longitude is not null
      and l.connectors_requiring_coordinate_review = 0
),

location_metrics as (
    select
        p.planning_area,
        p.region_name,
        p.provisional_location_id,

        z.expected_connectors,
        z.total_snapshots,
        z.complete_snapshots,
        z.zero_available_snapshots,
        z.all_occupied_snapshots

    from location_planning_area p

    join {{ ref('ev_location_zero_availability') }} z
        using (provisional_location_id)

    where p.planning_area is not null
)

select
    planning_area,
    region_name,

    count(distinct provisional_location_id)
        as charging_locations,

    sum(expected_connectors)
        as charging_points,

    sum(total_snapshots)
        as total_location_snapshots,

    sum(complete_snapshots)
        as complete_location_snapshots,

    sum(zero_available_snapshots)
        as zero_available_snapshots,

    sum(all_occupied_snapshots)
        as all_occupied_snapshots,

    round(
        100 * safe_divide(
            sum(zero_available_snapshots),
            sum(complete_snapshots)
        ),
        2
    ) as zero_availability_pct,

    round(
        100 * safe_divide(
            sum(all_occupied_snapshots),
            sum(complete_snapshots)
        ),
        2
    ) as all_occupied_pct,

    round(
        100 * safe_divide(
            sum(complete_snapshots),
            sum(total_snapshots)
        ),
        2
    ) as snapshot_completeness_pct

from location_metrics

group by
    planning_area,
    region_name
