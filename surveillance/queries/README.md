
surveillance/queries
Read-only versions of the two alert rules that `database/schema/schema.sql` writes into
`surveillance_alerts`:
`spoofing.sql`: order in the top 10% by size deleted within 1 ms of submission (HIGH)
`rapid_cancel.sql`: order deleted 1 to 50 ms after submission, not already a spoofing alert (MEDIUM)
`tests/integration/test_database.py` asserts each file returns exactly the rows in the alert table, so the
two copies cannot drift apart silently.