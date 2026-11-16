
WITH submit AS (
  SELECT DISTINCT ON (batch_id, order_id) batch_id, order_id, time_sec, size
  FROM market_messages WHERE event_type = 1 ORDER BY batch_id, order_id, source_record_number
), ended AS (
  SELECT DISTINCT ON (batch_id, order_id) batch_id, order_id, time_sec, event_type
  FROM market_messages WHERE event_type IN (3, 4) ORDER BY batch_id, order_id, source_record_number DESC
)
SELECT CASE e.event_type WHEN 3 THEN 'DELETED' WHEN 4 THEN 'EXECUTED' END AS ended_by,
       count(*)                                                        AS orders,
       round(avg((e.time_sec - s.time_sec) * 1000)::numeric, 2)        AS avg_lifetime_ms,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY (e.time_sec - s.time_sec) * 1000))::numeric, 2) AS median_lifetime_ms,
       round((percentile_cont(0.99) WITHIN GROUP (ORDER BY (e.time_sec - s.time_sec) * 1000))::numeric, 2) AS p99_lifetime_ms
FROM submit s JOIN ended e USING (batch_id, order_id)
WHERE e.time_sec >= s.time_sec
GROUP BY 1 ORDER BY 1;
