
WITH t AS (
  SELECT percentile_cont(0.9) WITHIN GROUP (ORDER BY size) AS p90
  FROM market_messages WHERE event_type = 1
)
SELECT s.batch_id, s.order_id, s.size, s.price_dollars, s.event_timestamp AS submitted_at,
       round(((d.time_sec - s.time_sec) * 1000)::numeric, 3) AS lifetime_ms
FROM market_messages s
JOIN market_messages d
  ON d.order_id = s.order_id AND d.batch_id = s.batch_id AND d.event_type = 3
WHERE s.event_type = 1
  AND NOT s.is_duplicate AND NOT d.is_duplicate
  AND d.time_sec - s.time_sec >= 0
  AND d.time_sec - s.time_sec < 0.001
  AND s.size >= (SELECT p90 FROM t)
ORDER BY s.size DESC, lifetime_ms;
