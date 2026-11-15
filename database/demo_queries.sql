
\echo '== 1. Pipeline reconciliation (source = loaded + rejected)'
SELECT * FROM v_pipeline_summary;

\echo '== 2. Lineage: batch, file, hash, version'
SELECT batch_id, source_file, trading_date, left(file_sha256, 12) AS sha256_prefix,
       pipeline_version, source_records, loaded_records, rejected_records
FROM import_batches;

\echo '== 3. Event mix'
SELECT event_label, count(*) AS messages,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
FROM market_messages GROUP BY 1 ORDER BY 2 DESC;

\echo '== 4. Rejected records by reason'
SELECT reject_reason, count(*) FROM rejected_messages GROUP BY 1 ORDER BY 2 DESC;

\echo '== 5. Surveillance alerts by type'
SELECT alert_type, severity, count(*) FROM surveillance_alerts GROUP BY 1, 2 ORDER BY 3 DESC;

\echo '== 6. Biggest spoofing candidates'
SELECT order_id, severity, description, detected_at
FROM surveillance_alerts WHERE alert_type = 'SPOOFING' ORDER BY detected_at LIMIT 10;

\echo '== 7. Database checks (all must be true)'
\i database/checks.sql
