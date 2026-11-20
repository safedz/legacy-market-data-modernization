-- Load the LOBSTER order book file for the latest batch into orderbook_snapshots.
-- Run from the PROJECT ROOT (the file path below is relative), after schema.sql and extras.sql:
--   psql -v ON_ERROR_STOP=1 -f database/load_orderbook.sql
-- Prices in the file are in 1/10000 dollars; the table stores dollars. Row n = book after message n.
-- All or nothing: if the row count differs from the batch's source_records the load is rolled back.
\set ON_ERROR_STOP on
CREATE TEMP TABLE staging_orderbook (
  rn            bigserial,
  ask_price_raw bigint,
  ask_size      integer,
  bid_price_raw bigint,
  bid_size      integer
);
\copy staging_orderbook (ask_price_raw, ask_size, bid_price_raw, bid_size) FROM 'data/raw/AAPL_2012-06-21_34200000_57600000_orderbook_1.csv' WITH (FORMAT csv)

BEGIN;
DELETE FROM orderbook_snapshots
 WHERE batch_id = (SELECT batch_id FROM import_batches ORDER BY ingestion_timestamp DESC, batch_id LIMIT 1);

INSERT INTO orderbook_snapshots (batch_id, source_record_number, ask_price, ask_size, bid_price, bid_size)
SELECT (SELECT batch_id FROM import_batches ORDER BY ingestion_timestamp DESC, batch_id LIMIT 1),
       rn, ask_price_raw / 10000.0, ask_size, bid_price_raw / 10000.0, bid_size
FROM staging_orderbook
ORDER BY rn;

DO $$
DECLARE
  expected bigint := (SELECT source_records FROM import_batches ORDER BY ingestion_timestamp DESC, batch_id LIMIT 1);
  loaded   bigint := (SELECT count(*) FROM orderbook_snapshots
                      WHERE batch_id = (SELECT batch_id FROM import_batches ORDER BY ingestion_timestamp DESC, batch_id LIMIT 1));
BEGIN
  IF expected IS DISTINCT FROM loaded THEN
    RAISE EXCEPTION 'Order book rows (%) do not match source records (%); load rolled back', loaded, expected;
  END IF;
END $$;
COMMIT;
SELECT count(*) AS orderbook_rows_loaded FROM orderbook_snapshots;
