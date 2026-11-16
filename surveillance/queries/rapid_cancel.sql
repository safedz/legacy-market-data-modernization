
SELECT s.batch_id, s.order_id, s.size, s.price_dollars, s.event_timestamp AS submitted_at,
       round(((d.time_sec - s.time_sec) * 1000)::numeric, 3) AS lifetime_ms
FROM market_messages s
JOIN market_messages d
  ON d.order_id = s.order_id AND d.batch_id = s.batch_id AND d.event_type = 3
WHERE s.event_type = 1
  AND NOT s.is_duplicate AND NOT d.is_duplicate
  AND d.time_sec - s.time_sec >= 0.001
  AND d.time_sec - s.time_sec < 0.05
  AND NOT EXISTS (SELECT 1 FROM surveillance_alerts a
                  WHERE a.alert_type = 'SPOOFING' AND a.order_id = s.order_id)
ORDER BY lifetime_ms, s.size DESC;
