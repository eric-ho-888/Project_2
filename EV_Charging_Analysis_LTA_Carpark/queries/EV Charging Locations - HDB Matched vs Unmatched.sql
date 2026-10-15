WITH charger_locations AS (
    SELECT
        ev_cp_id,

        -- Reconstruct the same provisional location ID
        -- used in ev_location_zero_availability
        TO_HEX(SHA256(TO_JSON_STRING(STRUCT(
            UPPER(TRIM(COALESCE(location_name, ''))),
            UPPER(TRIM(COALESCE(address, ''))),
            TRIM(COALESCE(postal_code, ''))
        )))) AS provisional_location_id

    FROM `chisq221.datamall_ev_charging.dim_charger`
),

strong_matches AS (
    SELECT DISTINCT
        ev_cp_id
    FROM `chisq221.datamall_ev_charging.bridge_ev_carpark`
    WHERE match_status = 'strong_candidate'
),

location_matching AS (
    SELECT
        c.provisional_location_id,

        COUNT(DISTINCT c.ev_cp_id) AS charging_points,

        COUNT(DISTINCT IF(
            s.ev_cp_id IS NOT NULL,
            c.ev_cp_id,
            NULL
        )) AS strongly_matched_points

    FROM charger_locations c

    LEFT JOIN strong_matches s
        ON c.ev_cp_id = s.ev_cp_id

    GROUP BY c.provisional_location_id
)

SELECT
    COUNT(*) AS total_charging_locations,

    COUNTIF(strongly_matched_points > 0)
        AS matched_charging_locations,

    COUNTIF(strongly_matched_points = 0)
        AS unmatched_charging_locations,

    ROUND(
        100 * SAFE_DIVIDE(
            COUNTIF(strongly_matched_points > 0),
            COUNT(*)
        ),
        2
    ) AS matched_location_pct,

    SUM(charging_points)
        AS total_charging_points

FROM location_matching;