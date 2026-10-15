SELECT
    ROW_NUMBER() OVER (
        ORDER BY occupancy_pct DESC
    ) AS occupancy_rank,
    planning_area,
    ROUND(occupancy_pct, 2) AS occupancy_pct,
    matched_charging_points,
    carparks_with_strong_ev_candidates,
    total_carparks
FROM `chisq221.datamall_ev_charging.planning_area_coverage_pressure`
WHERE occupancy_pct IS NOT NULL
  AND matched_charging_points > 0
ORDER BY occupancy_rank;