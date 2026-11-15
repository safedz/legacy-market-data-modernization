
SELECT date_trunc('second', event_timestamp)                         AS second,
       count(*)                                                      AS messages,
       count(*) FILTER (WHERE event_type = 1)                        AS submits,
       count(*) FILTER (WHERE event_type IN (2, 3))                  AS cancels,
       round((count(*) FILTER (WHERE event_type IN (2, 3)))::numeric
             / nullif(count(*) FILTER (WHERE event_type = 1), 0), 2) AS cancel_to_submit
FROM market_messages
GROUP BY 1
ORDER BY messages DESC
LIMIT 10;
