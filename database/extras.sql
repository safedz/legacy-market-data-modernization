-- Extra database objects: order book storage, constraints, indexes, audit trail, stored functions and
-- a stored procedure. Run AFTER database/schema/schema.sql (which drops and rebuilds the market tables)
-- and again every time schema.sql is re-run. Safe to run repeatedly.
--
--   psql -v ON_ERROR_STOP=1 -f database/extras.sql

-- 1. Order book snapshots (LOBSTER level 1) ---------------------------------------------------------
-- Row n of the order book file is the book AFTER message n, so (batch_id, source_record_number) joins
-- it to market_messages. No foreign key to import_batches on purpose: schema.sql drops and recreates
-- that table, and a foreign key would block it. checks_extra.sql verifies the link instead.
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
  batch_id             text    NOT NULL,
  source_record_number integer NOT NULL,
  ask_price            numeric(12,4) NOT NULL,
  ask_size             integer NOT NULL,
  bid_price            numeric(12,4) NOT NULL,
  bid_size             integer NOT NULL,
  PRIMARY KEY (batch_id, source_record_number),
  CONSTRAINT ck_ob_sizes CHECK (ask_size >= 0 AND bid_size >= 0)
);

-- schema.sql rebuilds import_batches but leaves this table alone, so drop snapshots whose batch no
-- longer exists (for example after the pipeline was re-run and produced a new batch id).
DELETE FROM orderbook_snapshots
 WHERE batch_id NOT IN (SELECT batch_id FROM import_batches);

-- 2. Constraints --------------------------------------------------------------------------------------
-- Type 7 is a trading halt; it carries no real size or price, so those rules skip it.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_mm_batch_record') THEN
    ALTER TABLE market_messages
      ADD CONSTRAINT uq_mm_batch_record UNIQUE (batch_id, source_record_number),
      ADD CONSTRAINT ck_mm_event_type CHECK (event_type BETWEEN 1 AND 7),
      ADD CONSTRAINT ck_mm_direction  CHECK (event_type = 7 OR direction IN (-1, 1)),
      ADD CONSTRAINT ck_mm_positive   CHECK (event_type = 7 OR (size > 0 AND price_dollars > 0));
    ALTER TABLE market_messages
      ALTER COLUMN batch_id SET NOT NULL,
      ALTER COLUMN source_record_number SET NOT NULL,
      ALTER COLUMN event_timestamp SET NOT NULL,
      ALTER COLUMN event_type SET NOT NULL,
      ALTER COLUMN order_id SET NOT NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_rej_batch_record') THEN
    ALTER TABLE rejected_messages
      ADD CONSTRAINT uq_rej_batch_record UNIQUE (batch_id, source_record_number),
      ADD CONSTRAINT ck_rej_reason CHECK (coalesce(reject_reason, '') <> '');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_batch_counts') THEN
    ALTER TABLE import_batches
      ADD CONSTRAINT ck_batch_counts CHECK (loaded_records >= 0 AND rejected_records >= 0 AND source_records >= 0);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_alert_severity') THEN
    ALTER TABLE surveillance_alerts
      ADD CONSTRAINT ck_alert_severity CHECK (severity IN ('HIGH', 'MEDIUM', 'LOW')),
      ALTER COLUMN alert_type SET NOT NULL,
      ALTER COLUMN order_id SET NOT NULL;
  END IF;
END $$;

-- 3. Indexes for the queries the dashboard and surveillance rules actually run ------------------------
CREATE INDEX IF NOT EXISTS idx_mm_batch_label ON market_messages (batch_id, event_label);
CREATE INDEX IF NOT EXISTS idx_alert_order    ON surveillance_alerts (order_id);
CREATE INDEX IF NOT EXISTS idx_alert_type     ON surveillance_alerts (alert_type, severity);
CREATE INDEX IF NOT EXISTS idx_rej_reason     ON rejected_messages (reject_reason);

-- 4. Audit trail ----------------------------------------------------------------------------------------
-- audit_log survives rebuilds (schema.sql does not drop it) and cannot be edited or emptied by
-- UPDATE / DELETE / TRUNCATE. A privileged user can still drop the trigger; this guards against
-- mistakes, not against the database owner.
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id    bigserial PRIMARY KEY,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  db_user     text        NOT NULL DEFAULT current_user,
  table_name  text        NOT NULL,
  operation   text        NOT NULL,
  row_count   bigint,
  row_key     text,
  details     jsonb
);

CREATE OR REPLACE FUNCTION fn_audit_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    INSERT INTO audit_log (table_name, operation, row_count, row_key, details)
    VALUES (TG_TABLE_NAME, TG_OP, 1, OLD.batch_id, jsonb_build_object('old', to_jsonb(OLD)));
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO audit_log (table_name, operation, row_count, row_key, details)
    VALUES (TG_TABLE_NAME, TG_OP, 1, NEW.batch_id,
            jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW)));
  ELSE
    INSERT INTO audit_log (table_name, operation, row_count, row_key, details)
    VALUES (TG_TABLE_NAME, TG_OP, 1, NEW.batch_id, jsonb_build_object('new', to_jsonb(NEW)));
  END IF;
  RETURN NULL;
END $$;

-- One audit row per bulk statement (with the row count) instead of one per row.
CREATE OR REPLACE FUNCTION fn_audit_statement() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE n bigint;
BEGIN
  IF TG_OP = 'DELETE' THEN
    EXECUTE 'SELECT count(*) FROM old_rows' INTO n;
  ELSE
    EXECUTE 'SELECT count(*) FROM new_rows' INTO n;
  END IF;
  INSERT INTO audit_log (table_name, operation, row_count) VALUES (TG_TABLE_NAME, TG_OP, n);
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION fn_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only (% is not allowed)', TG_OP;
END $$;

DROP TRIGGER IF EXISTS trg_audit_batches   ON import_batches;
DROP TRIGGER IF EXISTS trg_audit_mm_insert ON market_messages;
DROP TRIGGER IF EXISTS trg_audit_rej_insert ON rejected_messages;
DROP TRIGGER IF EXISTS trg_audit_alert_ins ON surveillance_alerts;
DROP TRIGGER IF EXISTS trg_audit_alert_del ON surveillance_alerts;
DROP TRIGGER IF EXISTS trg_audit_log_row   ON audit_log;
DROP TRIGGER IF EXISTS trg_audit_log_trunc ON audit_log;

CREATE TRIGGER trg_audit_batches AFTER INSERT OR UPDATE OR DELETE ON import_batches
  FOR EACH ROW EXECUTE FUNCTION fn_audit_row();
CREATE TRIGGER trg_audit_mm_insert AFTER INSERT ON market_messages
  REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_statement();
CREATE TRIGGER trg_audit_rej_insert AFTER INSERT ON rejected_messages
  REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_statement();
CREATE TRIGGER trg_audit_alert_ins AFTER INSERT ON surveillance_alerts
  REFERENCING NEW TABLE AS new_rows FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_statement();
CREATE TRIGGER trg_audit_alert_del AFTER DELETE ON surveillance_alerts
  REFERENCING OLD TABLE AS old_rows FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_statement();
CREATE TRIGGER trg_audit_log_row BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION fn_audit_immutable();
CREATE TRIGGER trg_audit_log_trunc BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_immutable();

-- 5. Stored functions ---------------------------------------------------------------------------------
-- Per-batch reconciliation: stored counts versus the rows really in the tables.
CREATE OR REPLACE FUNCTION fn_batch_report(p_batch text DEFAULT NULL)
RETURNS TABLE (batch_id text, source_records integer, loaded_records integer, rejected_records integer,
               actual_loaded bigint, actual_rejected bigint, reconciled boolean)
LANGUAGE sql STABLE AS $$
  SELECT b.batch_id, b.source_records, b.loaded_records, b.rejected_records,
         (SELECT count(*) FROM market_messages m WHERE m.batch_id = b.batch_id),
         (SELECT count(*) FROM rejected_messages r WHERE r.batch_id = b.batch_id),
         b.source_records = b.loaded_records + b.rejected_records
           AND b.loaded_records = (SELECT count(*) FROM market_messages m WHERE m.batch_id = b.batch_id)
           AND b.rejected_records = (SELECT count(*) FROM rejected_messages r WHERE r.batch_id = b.batch_id)
  FROM import_batches b
  WHERE p_batch IS NULL OR b.batch_id = p_batch
  ORDER BY b.ingestion_timestamp DESC, b.batch_id
$$;

-- Every message of one order in arrival order, with the best bid and ask right after it
-- (best_bid / best_ask are NULL until database/load_orderbook.sql has been run).
CREATE OR REPLACE FUNCTION fn_order_history(p_order bigint)
RETURNS TABLE (source_record_number integer, event_timestamp timestamp, event_label text, size integer,
               price_dollars numeric, direction smallint, best_bid numeric, best_ask numeric)
LANGUAGE sql STABLE AS $$
  SELECT m.source_record_number, m.event_timestamp, m.event_label, m.size,
         m.price_dollars::numeric, m.direction, o.bid_price::numeric, o.ask_price::numeric
  FROM market_messages m
  LEFT JOIN orderbook_snapshots o
         ON o.batch_id = m.batch_id AND o.source_record_number = m.source_record_number
  WHERE m.order_id = p_order
  ORDER BY m.time_sec, m.source_record_number
$$;

-- 6. Stored procedure: regenerate surveillance alerts with adjustable thresholds ------------------------
-- With the defaults it reproduces the alerts built by schema.sql exactly. Runs inside the caller's
-- transaction, so BEGIN ... CALL ... ROLLBACK can try other thresholds without changing anything.
CREATE OR REPLACE PROCEDURE sp_generate_alerts(
  p_spoof_ms numeric DEFAULT 1,
  p_rapid_ms numeric DEFAULT 50,
  p_size_percentile numeric DEFAULT 0.9)
LANGUAGE plpgsql AS $$
DECLARE
  n_spoof bigint;
  n_rapid bigint;
BEGIN
  IF p_spoof_ms IS NULL OR p_spoof_ms <= 0 THEN
    RAISE EXCEPTION 'p_spoof_ms must be greater than 0 (got %)', p_spoof_ms;
  END IF;
  IF p_rapid_ms IS NULL OR p_rapid_ms <= p_spoof_ms THEN
    RAISE EXCEPTION 'p_rapid_ms must be greater than p_spoof_ms (got % and %)', p_rapid_ms, p_spoof_ms;
  END IF;
  IF p_size_percentile IS NULL OR p_size_percentile <= 0 OR p_size_percentile >= 1 THEN
    RAISE EXCEPTION 'p_size_percentile must be between 0 and 1 (got %)', p_size_percentile;
  END IF;

  DELETE FROM surveillance_alerts;

  WITH t AS (
    SELECT percentile_cont(p_size_percentile) WITHIN GROUP (ORDER BY size) AS cutoff
    FROM market_messages WHERE event_type = 1
  )
  INSERT INTO surveillance_alerts (alert_type, order_id, severity, description, detected_at)
  SELECT 'SPOOFING', s.order_id, 'HIGH',
         'Large order cancelled within ' || (p_spoof_ms::float8)::text
           || ' ms of submission', s.event_timestamp
  FROM market_messages s
  JOIN market_messages d
    ON d.order_id = s.order_id AND d.batch_id = s.batch_id AND d.event_type = 3
  WHERE s.event_type = 1
    AND NOT s.is_duplicate AND NOT d.is_duplicate
    AND d.time_sec - s.time_sec >= 0
    AND d.time_sec - s.time_sec < p_spoof_ms / 1000.0
    AND s.size >= (SELECT cutoff FROM t);
  GET DIAGNOSTICS n_spoof = ROW_COUNT;

  INSERT INTO surveillance_alerts (alert_type, order_id, severity, description, detected_at)
  SELECT 'RAPID_CANCEL', s.order_id, 'MEDIUM',
         'Order cancelled within ' || (p_rapid_ms::float8)::text
           || ' ms of submission', s.event_timestamp
  FROM market_messages s
  JOIN market_messages d
    ON d.order_id = s.order_id AND d.batch_id = s.batch_id AND d.event_type = 3
  WHERE s.event_type = 1
    AND NOT s.is_duplicate AND NOT d.is_duplicate
    AND d.time_sec - s.time_sec >= p_spoof_ms / 1000.0
    AND d.time_sec - s.time_sec < p_rapid_ms / 1000.0
    AND NOT EXISTS (SELECT 1 FROM surveillance_alerts a
                    WHERE a.alert_type = 'SPOOFING' AND a.order_id = s.order_id);
  GET DIAGNOSTICS n_rapid = ROW_COUNT;

  RAISE NOTICE 'alerts regenerated: % spoofing, % rapid cancel', n_spoof, n_rapid;
END $$;

-- 7. Record the initial load. The triggers did not exist yet when schema.sql filled the tables, so
-- note that load explicitly (once per extras run; each run adds one set of rows).
INSERT INTO audit_log (table_name, operation, row_count, details)
SELECT t.name, 'LOAD', t.n, jsonb_build_object('note', 'rows loaded by schema.sql before the audit triggers existed')
FROM (SELECT 'import_batches' AS name, count(*) AS n FROM import_batches
      UNION ALL SELECT 'market_messages', count(*) FROM market_messages
      UNION ALL SELECT 'rejected_messages', count(*) FROM rejected_messages
      UNION ALL SELECT 'surveillance_alerts', count(*) FROM surveillance_alerts) t;
