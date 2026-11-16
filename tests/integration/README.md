
# Integration Tests

`test_database.py` runs the real pipeline, loads the output into PostgreSQL using the actual SQL files, and verifies that the database matches the pipeline results.

It checks:

- Record counts
- Lineage hash
- Rejection reasons
- Database validation checks
- Surveillance queries

## Run Integration Tests

**Important:** The test drops and recreates database tables. Always use a throwaway database.

Create a test database:

```bash
createdb pearl_test
```

Set the database connection variable (Windows CMD):

```cmd
set PEARL_TEST_DATABASE_URL=postgresql://surveillance_user:devpassword123@localhost:5432/pearl_test
```

Run the integration tests:

```bash
python -m pytest tests/integration -v
```

## Requirements

- PostgreSQL
- `psql` client available on PATH
- A dedicated test database

**Note:** Tests are automatically skipped if the environment variable or `psql` client is missing.

