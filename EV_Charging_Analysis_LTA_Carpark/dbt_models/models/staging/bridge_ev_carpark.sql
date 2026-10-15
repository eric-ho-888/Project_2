
{{ config(materialized='view') }}

with candidate_matches as (
    select
        -- HDB carpark fields
        c.carpark_id,
        c.car_park_no,
        c.address as carpark_address,
        c.latitude as carpark_latitude,
        c.longitude as carpark_longitude,

        -- EV charging point fields
        e.ev_cp_id,
        e.location_name,
        e.charging_point_name,
        e.address as charger_address,
        e.postal_code,
        e.latitude as charger_latitude,
        e.longitude as charger_longitude,

        -- Data quality indicators
        e.location_is_ambiguous,
        e.num_distinct_coords,
        e.max_distance_from_centroid_m,
        e.coordinate_review_required,

        -- Distance in metres
        st_distance(
            st_geogpoint(c.longitude, c.latitude),
            st_geogpoint(e.longitude, e.latitude)
        ) as distance_meters

    from {{ ref('dim_carpark') }} c

    join {{ ref('dim_charger') }} e
        on st_dwithin(
            st_geogpoint(c.longitude, c.latitude),
            st_geogpoint(e.longitude, e.latitude),
            100
        )

    where not e.coordinate_review_required
      and c.latitude is not null
      and c.longitude is not null
      and e.latitude is not null
      and e.longitude is not null
),

normalised as (
    select
        *,

        -- Normalise text without changing original fields
        trim(regexp_replace(
            regexp_replace(
                upper(carpark_address),
                r'\bBLK\b', 'BLOCK'
            ),
            r'\s+', ' '
        )) as carpark_address_normalised,

        trim(regexp_replace(
            regexp_replace(
                upper(charger_address),
                r'\bBLK\b', 'BLOCK'
            ),
            r'\s+', ' '
        )) as charger_address_normalised,

        trim(regexp_replace(
            regexp_replace(
                upper(location_name),
                r'\bBLK\b', 'BLOCK'
            ),
            r'\s+', ' '
        )) as location_name_normalised

    from candidate_matches
),

address_parts as (
    select
        *,

        -- Remove BLOCK prefix and leading block expression
        -- to obtain the street portion of the HDB address
        regexp_replace(
            regexp_replace(
                carpark_address_normalised,
                r'^BLOCK\s+[0-9A-Z/\-]+\s*', ''
            ),
            r'\s+', ' '
        ) as carpark_street,

        -- Remove leading block number and Singapore postal suffix
        trim(regexp_replace(
            regexp_replace(
                charger_address_normalised,
                r'^(BLOCK\s+)?[0-9]+[A-Z]?\s+', ''
            ),
            r'\s+SINGAPORE\s+\d{6}$', ''
        )) as charger_street,

        -- HDB leading block expression, e.g. 181-186 or 111/132
        regexp_extract(
            carpark_address_normalised,
            r'^BLOCK\s+([0-9A-Z/\-]+)\s'
        ) as carpark_block_expression,

        -- LTA individual block number, e.g. 186
        regexp_extract(
            charger_address_normalised,
            r'^(?:BLOCK\s+)?(\d+[A-Z]?)\s'
        ) as charger_block

    from normalised
),

block_checks as (
    select
        *,

        -- Compare street names
        (
            carpark_street = charger_street
            and carpark_street is not null
            and carpark_street != ''
        ) as street_matches,

        -- Numeric range: 181-186
        (
            regexp_contains(
                coalesce(carpark_block_expression, ''),
                r'^\d+-\d+$'
            )
            and safe_cast(charger_block as int64)
                between safe_cast(
                    split(carpark_block_expression, '-')[safe_offset(0)]
                    as int64
                )
                and safe_cast(
                    split(carpark_block_expression, '-')[safe_offset(1)]
                    as int64
                )
        ) as block_range_match,

        -- Explicit slash-separated blocks: 111/132
        (
            regexp_contains(
                coalesce(carpark_block_expression, ''),
                r'^\d+[A-Z]?(?:/\d+[A-Z]?)+$'
            )
            and charger_block in unnest(
                split(carpark_block_expression, '/')
            )
        ) as block_list_match

    from address_parts
),

matching_evidence as (
    select
        *,

        (
            carpark_address_normalised =
            charger_address_normalised
        ) as address_exact_match,

        (
            carpark_address_normalised =
            location_name_normalised
        ) as location_name_matches_carpark,

        (
            street_matches
            and (block_range_match or block_list_match)
        ) as block_and_street_match

    from block_checks
),

classified as (
    select
        *,

        case
            when distance_meters <= 50
                 and (
                     address_exact_match
                     or location_name_matches_carpark
                     or block_and_street_match
                 )
                then 'strong_candidate'

            when distance_meters > 50
                 and (
                     address_exact_match
                     or location_name_matches_carpark
                     or block_and_street_match
                 )
                then 'address_match_distance_review'

            when distance_meters <= 50
                then 'nearby_location_review'

            else 'review'
        end as match_status

    from matching_evidence
)

select *
from classified
