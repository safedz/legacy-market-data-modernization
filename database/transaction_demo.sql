-- Transactions in practice: try other alert thresholds, look at the result, then undo it all.
--   psql -f database/transaction_demo.sql
\echo '--- alerts before'
SELECT alert_type, count(*) FROM surveillance_alerts GROUP BY 1 ORDER BY 1;

BEGIN;
CALL sp_generate_alerts(5, 100, 0.5);    -- more sensitive: 5 ms / 100 ms / top 50% by size
\echo '--- alerts with the more sensitive thresholds (inside the transaction)'
SELECT alert_type, count(*) FROM surveillance_alerts GROUP BY 1 ORDER BY 1;
ROLLBACK;                                -- nothing above is kept

\echo '--- alerts after ROLLBACK (identical to before)'
SELECT alert_type, count(*) FROM surveillance_alerts GROUP BY 1 ORDER BY 1;

-- A savepoint undoes only part of a transaction.
BEGIN;
SAVEPOINT before_regenerate;
CALL sp_generate_alerts(2, 60, 0.8);
ROLLBACK TO SAVEPOINT before_regenerate; -- back to the state at the savepoint
COMMIT;
\echo '--- alerts after savepoint rollback (still identical)'
SELECT alert_type, count(*) FROM surveillance_alerts GROUP BY 1 ORDER BY 1;
