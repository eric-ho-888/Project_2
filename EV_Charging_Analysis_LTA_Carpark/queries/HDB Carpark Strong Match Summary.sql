SELECT
    SUM(total_carparks) AS total_hdb_carparks,
    SUM(carparks_with_strong_ev_candidates)
        AS carparks_with_strong_matches,
    SUM(carparks_without_strong_ev_candidates)
        AS carparks_without_strong_matches,
    SUM(matched_charging_points)
        AS matched_charging_points,
    ROUND(
        100 * SAFE_DIVIDE(
            SUM(carparks_with_strong_ev_candidates),
            SUM(total_carparks)
        ),
        2
    ) AS strong_match_coverage_pct
FROM `chisq221.datamall_ev_charging.planning_area_coverage_pressure`;