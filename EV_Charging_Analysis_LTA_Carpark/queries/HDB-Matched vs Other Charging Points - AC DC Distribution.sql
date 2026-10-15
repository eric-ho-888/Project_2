WITH matched_points AS (
    SELECT DISTINCT ev_cp_id
    FROM `chisq221.datamall_ev_charging.bridge_ev_carpark`
    WHERE match_status = 'strong_candidate'
),

classified_points AS (
    SELECT
        c.ev_cp_id,
        c.current AS charging_type,
        CASE
            WHEN m.ev_cp_id IS NOT NULL THEN 'HDB-matched'
            ELSE 'Not HDB-matched'
        END AS location_group
    FROM `chisq221.datamall_ev_charging.dim_charger` c
    LEFT JOIN matched_points m
        ON c.ev_cp_id = m.ev_cp_id
)

SELECT
    location_group,
    charging_type,
    COUNT(DISTINCT ev_cp_id) AS charging_points,
    ROUND(
        100 * SAFE_DIVIDE(
            COUNT(DISTINCT ev_cp_id),
            SUM(COUNT(DISTINCT ev_cp_id))
                OVER (PARTITION BY location_group)
        ),
        2
    ) AS percentage
FROM classified_points
GROUP BY location_group, charging_type
ORDER BY location_group, charging_points DESC;