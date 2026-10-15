SELECT
    `current` AS charging_type,
    COUNT(DISTINCT ev_cp_id) AS charging_points,
    ROUND(
        100 * SAFE_DIVIDE(
            COUNT(DISTINCT ev_cp_id),
            SUM(COUNT(DISTINCT ev_cp_id)) OVER ()
        ),
        2
    ) AS percentage
FROM `chisq221.datamall_ev_charging.dim_charger`
GROUP BY `current`
ORDER BY charging_points DESC;