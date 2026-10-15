
{{ config(materialized='view') }}

with planning_areas as (
    select
        *,
        st_geogfromtext(geometry_wkt) as planning_geometry
    from {{ source('datamall', 'ura_planning_areas_2025') }}
),

carpark_locations as (
    select
        *
    from {{ ref('dim_carpark') }}
)

select
    c.*,
    p.PLN_AREA_N as planning_area,
    p.REGION_N as region_name

from carpark_locations c

left join planning_areas p
    on st_covers(
        p.planning_geometry,
        st_geogpoint(c.longitude, c.latitude)
    )
