Runbook
Setup (once)
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

Run the pipeline
    python run_pipeline.py
Stages: ingest, transform, validate, quality. Exit code 1 means a reconciliation or quality gate failed;
read `data/processed/validation_report.json` and `quality_report.json`. Outputs (git-ignored):
File	Content
`data/processed/validated_messages.csv`, `data/rejected/rejected_messages.csv`	split result
`data/lake/raw/<batch>/`, `data/lake/curated/validated_messages.parquet`	lake zones
`data/processed/validation_report.json`	record reconciliation
`data/processed/quality_report.json`	order book reconciliation + lifecycle checks
`data/processed/profile_report.json`	data profile
`data/processed/run_manifest.json`	SHA-256 of every input and output
Tests
    python -m pytest -v                          # everything; database tests skip without PEARL_TEST_DATABASE_URL
    python quality-service/src/fault_injection.py --input data/raw/AAPL_2012-06-21_34200000_57600000_message_1.csv

Database
    docker compose -f deployment/docker-compose.yml up -d db
    .\database\rebuild_database.ps1
    psql -h localhost -U surveillance_user -d surveillance -f database/demo_queries.sql

Whole stack in Docker
    docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.data.yml up --build

Cloud
See `deployment/cloud/README.md`.
Troubleshooting
Symptom	Fix
`QUALITY GATE FAILED`	Open `quality_report.json`, look at `mismatch_samples`. Lower `--min-match-rate` only if the mismatches are explained
`Missing columns` in validation	Run all stages in order, do not mix outputs from different runs
`\copy` cannot find the CSV	Run `psql` from the project root, or use `rebuild_database.ps1`
`psql` not found	Install PostgreSQL client tools, or use the Docker route (no local psql needed)
