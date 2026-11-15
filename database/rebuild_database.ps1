
param(
  [string]$Container = "surveillance-db",
  [string]$Database = "surveillance",
  [string]$User = "surveillance_user",
  [switch]$SkipPipeline,
  [switch]$UseLocalPsql
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

if (-not $SkipPipeline) {
  Write-Host "== running pipeline" -ForegroundColor Cyan
  python run_pipeline.py
  if ($LASTEXITCODE -ne 0) { Fail "Pipeline failed - database not touched." }
}
foreach ($f in "data\processed\validated_messages.csv", "data\rejected\rejected_messages.csv") {
  if (-not (Test-Path $f)) { Fail "Missing $f - run python run_pipeline.py first." }
}

if ($UseLocalPsql) {
  $env:PGOPTIONS = "-c client_min_messages=warning"
  function Sql($file) { psql -v ON_ERROR_STOP=1 -q -f $file; if ($LASTEXITCODE -ne 0) { Fail "psql failed on $file" } }
  function Cmd($text) { psql -v ON_ERROR_STOP=1 -c $text; if ($LASTEXITCODE -ne 0) { Fail "psql failed: $text" } }
  $valid = "data/processed/validated_messages.csv"; $rejected = "data/rejected/rejected_messages.csv"
} else {
  function Sql($file) { Get-Content -Raw $file | docker exec -i -e "PGOPTIONS=-c client_min_messages=warning" $Container psql -U $User -d $Database -v ON_ERROR_STOP=1 -q; if ($LASTEXITCODE -ne 0) { Fail "psql failed on $file" } }
  function Cmd($text) { docker exec -i -e "PGOPTIONS=-c client_min_messages=warning" $Container psql -U $User -d $Database -v ON_ERROR_STOP=1 -c $text; if ($LASTEXITCODE -ne 0) { Fail "psql failed: $text" } }
  docker cp data\processed\validated_messages.csv "${Container}:/tmp/validated_messages.csv"
  docker cp data\rejected\rejected_messages.csv   "${Container}:/tmp/rejected_messages.csv"
  $valid = "/tmp/validated_messages.csv"; $rejected = "/tmp/rejected_messages.csv"
}

Write-Host "== staging table" -ForegroundColor Cyan;        Sql "database\staging.sql"
Write-Host "== loading staging" -ForegroundColor Cyan
Cmd "TRUNCATE staging_messages"
Cmd "\copy staging_messages FROM '$valid' WITH (FORMAT csv, HEADER true)"
Cmd "\copy staging_messages FROM '$rejected' WITH (FORMAT csv, HEADER true)"
Write-Host "== rebuilding derived tables" -ForegroundColor Cyan; Sql "database\schema\schema.sql"
Write-Host "== database checks" -ForegroundColor Cyan;      Sql "database\checks.sql"
Write-Host "Done. Try: database\demo_queries.sql" -ForegroundColor Green
