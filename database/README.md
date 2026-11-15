
# Database

PostgreSQL layer. Load order matters:

| Step | File | Purpose |
|---|---|---|
| 1 | `staging.sql` | Landing table whose columns match the pipeline CSVs one-to-one |
| 2 | `load_staging.sql` | `\copy` of `validated_messages.csv` and `rejected_messages.csv` (run from the project root) |
| 3 | `schema/schema.sql` | Rebuilds `import_batches`, `market_messages`, `rejected_messages`, `surveillance_alerts`, and `v_pipeline_summary` |
| 4 | `checks.sql` | Database-side reconciliation; every row must be `t` |

One command does all four:

**Windows (Docker database):**
```powershell
.\database\rebuild_database.ps1
```

**Windows (local psql installation):**
```powershell
.\database\rebuild_database.ps1 -UseLocalPsql
```

**Linux / Mac / CI:**
```bash
bash database/docker_load.sh
```

For local psql, use `MODE=local`.

### Additional Queries

- `demo_queries.sql` – Finals demonstration queries
- `order_lifecycle.sql`
- `burst_activity.sql`
- `../surveillance/queries/*.sql`
