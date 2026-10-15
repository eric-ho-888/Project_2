
WITH charger_locations AS (
    SELECT
        ev_cp_id,

        -- Same location grouping used in the existing dbt model
        TO_HEX(SHA256(TO_JSON_STRING(STRUCT(
            UPPER(TRIM(COALESCE(location_name, ''))),
            UPPER(TRIM(COALESCE(address, ''))),
            TRIM(COALESCE(postal_code, ''))
        )))) AS provisional_location_id

    FROM `chisq221.datamall_ev_charging.dim_charger`
),

strong_matches AS (
    SELECT DISTINCT ev_cp_id
    FROM `chisq221.datamall_ev_charging.bridge_ev_carpark`
    WHERE match_status = 'strong_candidate'
),

location_classification AS (
    SELECT
        c.provisional_location_id,

        CASE
            WHEN COUNTIF(s.ev_cp_id IS NOT NULL) > 0
                THEN 'HDB-matched'
            ELSE 'Not HDB-matched'
        END AS location_group

    FROM charger_locations c
    LEFT JOIN strong_matches s
        ON c.ev_cp_id = s.ev_cp_id

    GROUP BY c.provisional_location_id
),

location_metrics AS (
    SELECT
        c.location_group,
        z.provisional_location_id,
        z.total_snapshots,
        z.complete_snapshots,
        z.zero_available_snapshots,
        z.all_occupied_snapshots

    FROM `chisq221.datamall_ev_charging.ev_location_zero_availability` z

    JOIN location_classification c
        USING (provisional_location_id)
),

group_summary AS (
    SELECT
        location_group,
        COUNT(*) AS charging_locations,
        SUM(total_snapshots) AS total_snapshots,
        SUM(complete_snapshots) AS complete_snapshots,
        SUM(zero_available_snapshots) AS zero_available_snapshots,
        SUM(all_occupied_snapshots) AS all_occupied_snapshots
    FROM location_metrics
    GROUP BY location_group
),

final_summary AS (
    SELECT
        location_group,
        charging_locations,
        total_snapshots,
        complete_snapshots,

        ROUND(
            100 * SAFE_DIVIDE(
                complete_snapshots - zero_available_snapshots,
                complete_snapshots
            ), 2
        ) AS at_least_one_available_pct,

        ROUND(
            100 * SAFE_DIVIDE(
                zero_available_snapshots,
                complete_snapshots
            ), 2
        ) AS zero_availability_pct,

        ROUND(
            100 * SAFE_DIVIDE(
                all_occupied_snapshots,
                complete_snapshots
            ), 2
        ) AS all_occupied_pct

    FROM group_summary
)

SELECT *
FROM final_summary

UNION ALL

SELECT
    'Islandwide' AS location_group,
    SUM(charging_locations),
    SUM(total_snapshots),
    SUM(complete_snapshots),

    ROUND(
        100 * SAFE_DIVIDE(
            SUM(complete_snapshots - zero_available_snapshots),
            SUM(complete_snapshots)
        ), 2
    ),

    ROUND(
        100 * SAFE_DIVIDE(
            SUM(zero_available_snapshots),
            SUM(complete_snapshots)
        ), 2
    ),

    ROUND(
        100 * SAFE_DIVIDE(
            SUM(all_occupied_snapshots),
            SUM(complete_snapshots)
        ), 2
    )

FROM group_summary

ORDER BY location_group;
