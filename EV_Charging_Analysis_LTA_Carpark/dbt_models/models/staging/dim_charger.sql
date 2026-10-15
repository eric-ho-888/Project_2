
with charger_values as (
    select
        ev_cp_id,
        location_name,
        charging_point_name,
        address,
        postal_code,
        latitude,
        longitude,
        operator,
        position,
        operating_hours,
        plug_type,
        `current`,
        power_rating,
        price_type,
        snapshot_time,

        -- Standardise location names for comparison only.
        -- Original location_name remains unchanged.
        trim(
            regexp_replace(
                upper(
                    replace(location_name, chr(92), '')
                ),
                r'\s+',
                ' '
            )
        ) as location_name_standardised

    from {{ source('datamall', 'ev_charging_points') }}
),

charger_summary as (
    select
        ev_cp_id,

        -- Latest recorded charger attributes
        array_agg(location_name
            order by snapshot_time desc)[offset(0)]
            as location_name,

        array_agg(charging_point_name
            order by snapshot_time desc)[offset(0)]
            as charging_point_name,

        array_agg(address
            order by snapshot_time desc)[offset(0)]
            as address,

        array_agg(postal_code
            order by snapshot_time desc)[offset(0)]
            as postal_code,

        array_agg(operator
            order by snapshot_time desc)[offset(0)]
            as operator,

        array_agg(position
            order by snapshot_time desc)[offset(0)]
            as position,

        array_agg(operating_hours
            order by snapshot_time desc)[offset(0)]
            as operating_hours,

        array_agg(plug_type
            order by snapshot_time desc)[offset(0)]
            as plug_type,

        array_agg(`current`
            order by snapshot_time desc)[offset(0)]
            as `current`,

        safe_cast(
            array_agg(power_rating
                order by snapshot_time desc)[offset(0)]
            as float64
        ) as power_rating_kw,

        array_agg(price_type
            order by snapshot_time desc)[offset(0)]
            as price_type,

        -- Average reported coordinates
        avg(latitude) as latitude,
        avg(longitude) as longitude,

        -- Preserve original names
        array_agg(distinct location_name)
            as all_location_names_seen,

        -- Compare standardised names
        count(distinct location_name_standardised) > 1
            as location_is_ambiguous,

        -- Existing record count
        count(*) as num_snapshots,

        -- Original distinct-name count (unchanged)
        count(distinct location_name)
            as num_distinct_location_names,

        -- New: distinct names after standardisation
        count(distinct location_name_standardised)
            as num_distinct_location_names_standardised,

        -- New: identify formatting-only differences
        (
            count(distinct location_name) > 1
            and count(distinct location_name_standardised) = 1
        ) as name_variation_formatting_only,

        -- Existing coordinate count
        count(distinct concat(
            cast(latitude as string),
            ',',
            cast(longitude as string)
        )) as num_distinct_coords

    from charger_values
    group by ev_cp_id
),

coordinate_spread as (
    select
        v.ev_cp_id,

        -- Maximum distance from average coordinates
        max(
            st_distance(
                st_geogpoint(
                    v.longitude,
                    v.latitude
                ),
                st_geogpoint(
                    s.longitude,
                    s.latitude
                )
            )
        ) as max_distance_from_centroid_m

    from charger_values v

    join charger_summary s
        on v.ev_cp_id = s.ev_cp_id

    where v.latitude is not null
      and v.longitude is not null
      and s.latitude is not null
      and s.longitude is not null

    group by v.ev_cp_id
)

select
    s.*,

    -- Maximum geographic deviation in metres
    round(
        c.max_distance_from_centroid_m,
        2
    ) as max_distance_from_centroid_m,

    -- Flag substantial coordinate inconsistencies
    coalesce(
        c.max_distance_from_centroid_m > 50,
        true
    ) as coordinate_review_required

from charger_summary s

left join coordinate_spread c
    on s.ev_cp_id = c.ev_cp_id
