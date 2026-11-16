"""Edge cases for validate_data, one rule at a time."""
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for s in ("ingestion-service", "transformation-service", "validation-service"):
    sys.path.insert(0, str(ROOT / s / "src"))

from ingest import ingest_data
from transform import transform_data
from validate_data import validate_data

NAME = "T_2012-06-21_34200000_57600000_message_1.csv"


def run(tmp_path, rows):
    src = tmp_path / NAME
    src.write_text("\n".join(rows) + "\n", encoding="utf-8")
    data = tmp_path / "data"
    ingest_data(src, data)
    transform_data(data)
    report = validate_data(data)
    rejected = pd.read_csv(data / "rejected" / "rejected_messages.csv")
    return report, rejected


@pytest.mark.parametrize("row,code", [
    ("34200.1,1,1,10,-5,1", "INVALID_PRICE"),
    ("34200.1,1,1,10,0,1", "INVALID_PRICE"),
    ("34200.1,1,1,10,1000,0", "INVALID_DIRECTION"),
    ("34200.1,1,1,10,1000,2", "INVALID_DIRECTION"),
    ("34200.1,0,1,10,1000,1", "INVALID_EVENT_TYPE"),
    ("34200.1,8,1,10,1000,1", "INVALID_EVENT_TYPE"),
    ("86400.0,1,1,10,1000,1", "INVALID_TIME"),
    ("-1.0,1,1,10,1000,1", "INVALID_TIME"),
    ("34200.1,1,1,-3,1000,1", "INVALID_SIZE"),
    ("abc,1,1,10,1000,1", "MISSING_OR_NON_NUMERIC"),
    ("34200.1,1,1,,1000,1", "MISSING_OR_NON_NUMERIC"),
])
def test_single_rule_rejects(tmp_path, row, code):
    report, rejected = run(tmp_path, ["34200.0,1,9,10,1000,1", row])
    assert report["reconciliation_pass"] is True
    assert report["stages"]["rejected"]["records"] == 1
    assert code in rejected.iloc[0]["reject_reason"]


@pytest.mark.parametrize("row", [
    "34200.1,7,0,0,-1,-1",
    "34200.1,7,0,0,0,-1",
    "34200.1,7,0,0,1,-1",
])
def test_valid_halts_pass(tmp_path, row):
    report, _ = run(tmp_path, [row])
    assert report["stages"]["rejected"]["records"] == 0


@pytest.mark.parametrize("row", [
    "34200.1,7,5,0,-1,-1",  
    "34200.1,7,0,3,-1,-1",  
    "34200.1,7,0,0,-1,1",    
    "34200.1,7,0,0,500,-1", 
])
def test_bad_halts_rejected(tmp_path, row):
    _, rejected = run(tmp_path, [row])
    assert "INVALID_HALT_FIELDS" in rejected.iloc[0]["reject_reason"]


def test_multiple_reasons_are_all_recorded(tmp_path):
    _, rejected = run(tmp_path, ["34200.1,1,1,0,-5,0"])
    reason = rejected.iloc[0]["reject_reason"]
    assert {"INVALID_SIZE", "INVALID_PRICE", "INVALID_DIRECTION"} <= set(reason.split(";"))


def test_duplicates_are_flagged_but_kept(tmp_path):
    report, _ = run(tmp_path, ["34200.1,1,1,10,1000,1"] * 3)
    assert report["duplicate_rows_flagged"] == 2
    assert report["stages"]["valid"]["records"] == 3


def test_all_rejected_batch_still_reconciles(tmp_path):
    report, rejected = run(tmp_path, ["34200.1,9,1,10,1000,1", "34200.2,9,2,10,1000,1"])
    assert report["reconciliation_pass"] is True
    assert len(rejected) == 2
