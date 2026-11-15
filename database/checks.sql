
SELECT * FROM (
  SELECT 'staging rows = market + rejected' AS check_name,
         (SELECT count(*) FROM staging_messages)
           = (SELECT count(*) FROM market_messages) + (SELECT count(*) FROM rejected_messages) AS passed
  UNION ALL
  SELECT 'import_batches counts match tables',
         (SELECT sum(loaded_records) FROM import_batches) = (SELECT count(*) FROM market_messages)
         AND (SELECT sum(rejected_records) FROM import_batches) = (SELECT count(*) FROM rejected_messages)
  UNION ALL
  SELECT 'pipeline summary view reconciled',
         (SELECT reconciled FROM v_pipeline_summary)
  UNION ALL
  SELECT 'no market message without a batch',
         NOT EXISTS (SELECT 1 FROM market_messages m LEFT JOIN import_batches b USING (batch_id)
                     WHERE b.batch_id IS NULL)
  UNION ALL
  SELECT 'record numbers unique per batch',
         NOT EXISTS (SELECT 1 FROM (
           SELECT batch_id, source_record_number FROM market_messages
           UNION ALL SELECT batch_id, source_record_number FROM rejected_messages) u
           GROUP BY batch_id, source_record_number HAVING count(*) > 1)
  UNION ALL
  SELECT 'no non-positive size or price in market_messages',
         NOT EXISTS (SELECT 1 FROM market_messages
                     WHERE event_type <> 7 AND (size <= 0 OR price_dollars <= 0))
  UNION ALL
  SELECT 'every rejected row has a reason',
         NOT EXISTS (SELECT 1 FROM rejected_messages WHERE coalesce(reject_reason,'') = '')
) c ORDER BY check_name;
