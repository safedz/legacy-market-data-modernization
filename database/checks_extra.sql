-- Extra database-side checks. Every row must say passed = true. Run after extras.sql.
SELECT * FROM (
  SELECT 'every batch reconciles (fn_batch_report)' AS check_name,
         coalesce((SELECT bool_and(reconciled) FROM fn_batch_report()), false) AS passed
  UNION ALL
  SELECT 'all constraints are in place',
         (SELECT count(*) FROM pg_constraint WHERE conname IN
            ('uq_mm_batch_record','ck_mm_event_type','ck_mm_direction','ck_mm_positive',
             'uq_rej_batch_record','ck_rej_reason','ck_batch_counts','ck_alert_severity')) = 8
  UNION ALL
  SELECT 'all audit triggers are in place',
         (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname IN
            ('trg_audit_batches','trg_audit_mm_insert','trg_audit_rej_insert','trg_audit_alert_ins',
             'trg_audit_alert_del','trg_audit_log_row','trg_audit_log_trunc')) = 7
  UNION ALL
  SELECT 'audit log has the initial load recorded',
         EXISTS (SELECT 1 FROM audit_log WHERE operation = 'LOAD' AND table_name = 'market_messages')
  UNION ALL
  SELECT 'order book is empty or covers every source record of the latest batch',
         (SELECT count(*) FROM orderbook_snapshots) = 0
         OR (SELECT count(*) FROM orderbook_snapshots
             WHERE batch_id = (SELECT batch_id FROM import_batches ORDER BY ingestion_timestamp DESC, batch_id LIMIT 1))
          = (SELECT source_records FROM import_batches ORDER BY ingestion_timestamp DESC, batch_id LIMIT 1)
  UNION ALL
  SELECT 'order book rows all belong to a known batch',
         NOT EXISTS (SELECT 1 FROM orderbook_snapshots o LEFT JOIN import_batches b USING (batch_id)
                     WHERE b.batch_id IS NULL)
  UNION ALL
  SELECT 'every alert refers to an order in market_messages',
         NOT EXISTS (SELECT 1 FROM surveillance_alerts a
                     WHERE NOT EXISTS (SELECT 1 FROM market_messages m WHERE m.order_id = a.order_id))
) c ORDER BY check_name;
