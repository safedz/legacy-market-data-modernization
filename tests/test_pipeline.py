from pathlib import Path
import hashlib
import json
import sys

import pandas as pd
import pytest

ROOT =Path(__file__).resolve().parents[1]
sys.path.insert(0, str (ROOT))
for service in ("ingestion-service", "transformation-service","validation-service"):
    sys.path.insert(0,str(ROOT / service / "src"))

from ingest import ingest_data
from transform import transform_data
from validate_data import validate_data

SAMPLE_ROWS = """34200.004241176,1,100,50,2000000,1
34200.500000000,2,100,20,2000000,1
34201.000000000,3,100,30,2000000,1
34202.000000000,4,200,10,2010000,-1
34203.000000000,7,0,0,-1,-1
34204.000000000,1,300,0,2000000,1
34205.000000000,9,400,10,2000000,1
"""

SAMPLE_NAME = "TEST_2012-06-21_34200000_57600000_message_1.csv"

@pytest.fixture
def run(tmp_path):
    sample = tmp_path / SAMPLE_NAME
    sample.write_text(SAMPLE_ROWS, encoding="utf-8")
    data_dir = tmp_path / "data"
    ingest_data(sample, data_dir)
    transform_data(data_dir)
    report = validate_data(data_dir)
    return sample, data_dir, report

def test_transform_passes_every_row(run):
    _, data_dir, _ = run
    transformed= pd.read_csv(data_dir / "processed" / "transformed_messages.csv" )
    assert len(transformed) == 7

def test_counts_split_into_valid_and_rejected(run):
    _, _, report = run
    assert report["stages"]["valid"]["records"] == 5
    assert report["stages"]["rejected"]["records"] == 2

def test_reconciliation_passes(run):
    _, _, report = run
    assert report["reconciliation_pass"] is True
    assert all(report["reconciliation"].values())

def test_reject_reasons_recorded(run):
    _, data_dir, _ = run
    rejected = pd.read_csv(data_dir / "rejected" / "rejected_messages.csv")
    reasons = set(rejected["reject_reason"])
    assert reasons == {"INVALID_SIZE", "INVALID_EVENT_TYPE"}

def test_halt_is_kept_as_valid(run):
    _, data_dir, _ = run
    valid = pd.read_csv(data_dir / "processed" / "validated_messages.csv")
    assert 7 in set(valid["event_type"])

def test_price_scaled_to_dollars(run):
    _, data_dir, _ = run
    valid = pd.read_csv(data_dir / "processed" / "validated_messages.csv")
    first = valid.loc[valid["source_record_number"] == 1, "price_dollars"].iloc[0]
    assert first == 200.0


def test_timestamp_built_from_filename_date(run):
    _, data_dir, _ = run
    valid = pd.read_csv(data_dir / "processed" / "validated_messages.csv")
    assert str(valid.iloc[0]["event_timestamp"]).startswith("2012-06-21 09:30:00")

def test_lineage_and_raw_copy(run):
    sample, data_dir, _ = run
    manifest = json.loads(
        (data_dir / "processed" / "manifest.json").read_text(encoding="utf-8")
    )
    expected = hashlib.sha256(sample.read_bytes()).hexdigest()
    assert manifest["file_sha256"] == expected

    raw_copy = Path(manifest["lake_raw_copy"])
    assert hashlib.sha256(raw_copy.read_bytes()).hexdigest() == expected

    valid = pd.read_csv(data_dir / "processed" / "validated_messages.csv")
    for column in ("source_file", "source_record_number", "file_sha256", "batch_id"):
        assert valid[column].notna().all()


def test_curated_parquet_written(run):
    _, data_dir, _ = run
    curated = pd.read_parquet(data_dir / "lake" / "curated" / "validated_messages.parquet")
    assert len(curated) == 5