
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "quality-service" / "src", *(ROOT / s / "src" for s in
          ("ingestion-service", "transformation-service", "validation-service"))):
    sys.path.insert(0, str(p))

URL = os.environ.get("PEARL_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL or shutil.which("psql") is None,
    reason="set PEARL_TEST_DATABASE_URL and install psql to run database tests",
)


def psql(*args, cwd=ROOT, check=True):
    result = subprocess.run(["psql", URL, "-v", "ON_ERROR_STOP=1", "-q", *args],
                            cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"psql failed: {result.stderr}\n{result.stdout}")
    return result.stdout.strip()


def scalar(sql):
    return psql("-At", "-c", sql)


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    from fault_injection import inject_faults
    from ingest import ingest_data
    from lobster_sim import write_files
    from transform import transform_data
    from validate_data import validate_data

    work = tmp_path_factory.mktemp("dbrun")
    msg, _ = write_files(work / "src", n_messages=3000)
    corrupted = work / msg.name
    inject_faults(msg, corrupted, per_fault=2)  
    data = work / "data"
    ingest_data(corrupted, data)
    transform_data(data)
    report = validate_data(data)

    psql("-f", str(ROOT / "database" / "staging.sql"))
    psql("-f", str(ROOT / "database" / "load_staging.sql"), cwd=work)  
    psql("-f", str(ROOT / "database" / "schema" / "schema.sql"))
    return report


def test_counts_match_pipeline_report(loaded):
    assert int(scalar("select count(*) from market_messages")) == loaded["stages"]["valid"]["records"]
    assert int(scalar("select count(*) from rejected_messages")) == loaded["stages"]["rejected"]["records"]
    assert loaded["stages"]["rejected"]["records"] > 0


def test_summary_view_reconciles(loaded):
    assert scalar("select reconciled from v_pipeline_summary") == "t"
    assert int(scalar("select source_records from v_pipeline_summary")) == loaded["stages"]["raw"]["records"]


def test_lineage_hash_matches_manifest(loaded):
    assert scalar("select file_sha256 from import_batches") == loaded["file_sha256"]


def test_reject_reasons_match(loaded):
    rows = psql("-At", "-F", "|", "-c",
                "select reject_reason, count(*) from rejected_messages group by 1")
    db = {r.split("|")[0]: int(r.split("|")[1]) for r in rows.splitlines()}
    assert sum(db.values()) == loaded["stages"]["rejected"]["records"]


def test_all_database_checks_pass(loaded):
    out = psql("-At", "-F", "|", "-f", str(ROOT / "database" / "checks.sql"))
    results = [line.split("|") for line in out.splitlines() if "|" in line]
    assert results and all(passed == "t" for _, passed in results), results


def test_surveillance_query_files_agree_with_alerts(loaded):
    for name, alert in (("spoofing", "SPOOFING"), ("rapid_cancel", "RAPID_CANCEL")):
        sql = (ROOT / "surveillance" / "queries" / f"{name}.sql").read_text()
        sql = "\n".join(l for l in sql.splitlines() if not l.startswith("--")).strip().rstrip(";")
        rows = len(psql("-At", "-c", sql).splitlines())
        assert rows == int(scalar(f"select count(*) from surveillance_alerts where alert_type='{alert}'"))
