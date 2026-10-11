SELECT
  operator,
  COUNT(DISTINCT ev_cp_id) AS charging_points,
  COUNT(DISTINCT IF(price > 0, ev_cp_id, NULL))
    AS charging_points_with_positive_price,
  ROUND(AVG(IF(price > 0, price, NULL)), 3)
    AS avg_price_per_kwh,
  ROUND(MIN(IF(price > 0, price, NULL)), 3)
    AS min_price_per_kwh,
  ROUND(MAX(IF(price > 0, price, NULL)), 3)
    AS max_price_per_kwh
FROM `sg-ev-510713.ev_raw.ev_charging_raw`
WHERE LOWER(TRIM(price_type)) = 'kwh'
GROUP BY operator
HAVING COUNT(DISTINCT ev_cp_id) >= 100
ORDER BY avg_price_per_kwh ASC;
