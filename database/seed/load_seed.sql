
\set ON_ERROR_STOP on
\i database/staging.sql
TRUNCATE staging_messages;
\copy staging_messages FROM 'data/sim/data/processed/validated_messages.csv' WITH (FORMAT csv, HEADER true)
\copy staging_messages FROM 'data/sim/data/rejected/rejected_messages.csv' WITH (FORMAT csv, HEADER true)
SELECT validation_status, count(*) FROM staging_messages GROUP BY 1 ORDER BY 1;
