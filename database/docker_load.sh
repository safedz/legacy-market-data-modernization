
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${MODE:-docker}"
export PGOPTIONS="${PGOPTIONS:--c client_min_messages=warning}"   
CONTAINER="${CONTAINER:-surveillance-db}"
DB="${PGDATABASE:-surveillance}"
DB_USER="${PGUSER:-surveillance_user}"

for f in data/processed/validated_messages.csv data/rejected/rejected_messages.csv; do
  [ -f "$f" ] || { echo "Missing $f - run: python run_pipeline.py" >&2; exit 1; }
done

if [ "$MODE" = "docker" ]; then
  psql_run() { docker exec -i -e PGOPTIONS="$PGOPTIONS" "$CONTAINER" psql -U "$DB_USER" -d "$DB" -v ON_ERROR_STOP=1 "$@"; }
  docker cp data/processed/validated_messages.csv "$CONTAINER:/tmp/validated_messages.csv"
  docker cp data/rejected/rejected_messages.csv   "$CONTAINER:/tmp/rejected_messages.csv"
  VALID=/tmp/validated_messages.csv; REJ=/tmp/rejected_messages.csv
  schema_input() { docker exec -i -e PGOPTIONS="$PGOPTIONS" "$CONTAINER" psql -U "$DB_USER" -d "$DB" -v ON_ERROR_STOP=1 -q < "$1"; }
else
  psql_run() { psql -v ON_ERROR_STOP=1 "$@"; }
  VALID=data/processed/validated_messages.csv; REJ=data/rejected/rejected_messages.csv
  schema_input() { psql -v ON_ERROR_STOP=1 -q -f "$1"; }
fi

echo "== staging table";   schema_input database/staging.sql
echo "== loading staging"
psql_run -c "TRUNCATE staging_messages"
psql_run -c "\\copy staging_messages FROM '$VALID' WITH (FORMAT csv, HEADER true)"
psql_run -c "\\copy staging_messages FROM '$REJ' WITH (FORMAT csv, HEADER true)"
echo "== rebuilding derived tables"; schema_input database/schema/schema.sql
echo "== database checks";  schema_input database/checks.sql
