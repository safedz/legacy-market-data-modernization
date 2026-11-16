
# Surveillance Queries

Read-only versions of the two alert rules that `database/schema/schema.sql` writes into `surveillance_alerts`.

## Alert Rules

| File | Description | Severity |
|---|---|---|
| `spoofing.sql` | Identifies orders in the top 10% by size that are deleted within 1 ms of submission. | HIGH |
| `rapid_cancel.sql` | Identifies orders deleted between 1 and 50 ms after submission, excluding orders already flagged as spoofing alerts. | MEDIUM |

## Integration Tests

`tests/integration/test_database.py` verifies that each SQL file returns exactly the same rows as the corresponding records in the `surveillance_alerts` table.

This ensures that the standalone query files and database alert rules remain consistent and cannot silently drift apart.
