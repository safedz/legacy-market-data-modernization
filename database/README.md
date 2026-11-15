database
PostgreSQL layer. Load order matters:
Step	File	Purpose
1	`staging.sql`	Landing table whose columns match the pipeline CSVs one-to-one
2	`load\_staging.sql`	`\\copy` of `validated\_messages.csv` and `rejected\_messages.csv` (run from the project root)
3	`schema/schema.sql`	Rebuilds `import\_batches`, `market\_messages`, `rejected\_messages`, `surveillance\_alerts`, `v\_pipeline\_summary`
4	`checks.sql`	Database-side reconciliation, every row must be `t`
One command does all four:
    .\database\rebuild_database.ps1                # Windows, Docker database
.\database\rebuild_database.ps1 -UseLocalPsql  # Windows, psql installed locally
bash database/docker_load.sh                   # Linux / Mac / CI (MODE=local for local psql)

Extra queries: `demo\_queries.sql` (finals demo), `order\_lifecycle.sql`, `burst\_activity.sql`,
and `../surveillance/queries/\*.sql`.