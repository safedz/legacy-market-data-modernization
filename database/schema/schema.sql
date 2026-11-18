-- Rebuild derived objects (staging_messages is left alone)
DROP VIEW  IF EXISTS v_pipeline_summary;
DROP TABLE IF EXISTS surveillance_alerts;
DROP TABLE IF EXISTS rejected_messages;
DROP TABLE IF EXISTS market_messages;
DROP TABLE IF EXISTS import_batches;


CREATE TABLE import_batches (
  batch_id text PRIMARY KEY,
  source_file text,
  trading_date date,
  file_sha256 text,
  pipeline_version text,
  ingestion_timestamp timestamptz,
  source_records integer,
  loaded_records integer,
  rejected_records integer
);

INSERT INTO import_batches
SELECT batch_id, max(source_file), max(trading_date), max(file_sha256),
       max(pipeline_version), max(ingestion_timestamp), count(*),
       count(*) FILTER (WHERE validation_status = 'VALID'),
       count(*) FILTER (WHERE validation_status = 'REJECTED')
FROM staging_messages
GROUP BY batch_id;

-- 2. Valid and rejected messages
CREATE TABLE market_messages (
  message_id bigserial PRIMARY KEY,
  batch_id text REFERENCES import_batches(batch_id),
  source_record_number integer,
  event_timestamp timestamp,
  time_sec double precision,
  event_type smallint,
  event_label text,
  order_id bigint,
  size integer,
  price_dollars numeric(12,4),
  direction smallint,
  is_duplicate boolean
);

INSERT INTO market_messages (batch_id, source_record_number, event_timestamp, time_sec,
  event_type, event_label, order_id, size, price_dollars, direction, is_duplicate)
SELECT batch_id, source_record_number, event_timestamp, time_sec,
  event_type, event_label, order_id, size, price_dollars, direction, is_duplicate
FROM staging_messages
WHERE validation_status = 'VALID';

CREATE TABLE rejected_messages (
  rejected_id bigserial PRIMARY KEY,
  batch_id text REFERENCES import_batches(batch_id),
  source_record_number integer,
  order_id bigint,
  reject_reason text
);

INSERT INTO rejected_messages (batch_id, source_record_number, order_id, reject_reason)
SELECT batch_id, source_record_number, order_id, reject_reason
FROM staging_messages
WHERE validation_status = 'REJECTED';

CREATE INDEX idx_mm_order ON market_messages (order_id, event_type);
CREATE INDEX idx_mm_time  ON market_messages (event_timestamp);

-- 3. Surveillance alerts
CREATE TABLE surveillance_alerts (
  alert_id bigserial PRIMARY KEY,
  alert_type text,
  order_id bigint,
  severity text,
  description text,
  detected_at timestamp
);

-- Spoofing: large order (top 10% by size) deleted within 1 ms of submission
WITH t AS (
  SELECT percentile_cont(0.9) WITHIN GROUP (ORDER BY size) AS p90
  FROM market_messages WHERE event_type = 1
)
INSERT INTO surveillance_alerts (alert_type, order_id, severity, description, detected_at)
SELECT 'SPOOFING', s.order_id, 'HIGH',
       'Large order cancelled within 1 ms of submission', s.event_timestamp
FROM market_messages s
JOIN market_messages d
  ON d.order_id = s.order_id AND d.batch_id = s.batch_id AND d.event_type = 3
WHERE s.event_type = 1
  AND NOT s.is_duplicate AND NOT d.is_duplicate
  AND d.time_sec - s.time_sec >= 0
  AND d.time_sec - s.time_sec < 0.001
  AND s.size >= (SELECT p90 FROM t);

-- Rapid cancel: deleted within 50 ms, not already flagged as spoofing
INSERT INTO surveillance_alerts (alert_type, order_id, severity, description, detected_at)
SELECT 'RAPID_CANCEL', s.order_id, 'MEDIUM',
       'Order cancelled within 50 ms of submission', s.event_timestamp
FROM market_messages s
JOIN market_messages d
  ON d.order_id = s.order_id AND d.batch_id = s.batch_id AND d.event_type = 3
WHERE s.event_type = 1
  AND NOT s.is_duplicate AND NOT d.is_duplicate
  AND d.time_sec - s.time_sec >= 0.001
  AND d.time_sec - s.time_sec < 0.05
  AND NOT EXISTS (SELECT 1 FROM surveillance_alerts a
                  WHERE a.alert_type = 'SPOOFING' AND a.order_id = s.order_id);

-- 4. Dashboard summary
CREATE VIEW v_pipeline_summary AS
SELECT sum(source_records) AS source_records,
       sum(loaded_records) AS loaded_records,
       sum(rejected_records) AS rejected_records,
       sum(source_records) = sum(loaded_records) + sum(rejected_records) AS reconciled,
       max(ingestion_timestamp) AS last_run
FROM import_batches;