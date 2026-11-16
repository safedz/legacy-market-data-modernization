from pathlib import Path
import hashlib
import json
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ingestion-service" / "src"))

from ingest import count_lines, ingest_data, sha256_of
from common.schema import INGESTED_COLUMNS

NAME = "T_2012-06-21_34200000_57600000_message_1.csv"
ROWS = "34200.1,1,10,5,1000,1\n34200.2,3,10,5,1000,1\n"


@pytest.fixture
def ingested(tmp_path):
    src = tmp_path / NAME
    src.write_text(ROWS, encoding="utf-8")
    manifest = ingest_data(src, tmp_path / "data")
    return src, tmp_path / "data", manifest


def test_missing_input_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest_data(tmp_path / "nope.csv", tmp_path / "data")


def test_output_has_expected_columns_and_rows(ingested):
    _, data, _ = ingested
    out = pd.read_csv(data / "processed" / "ingested_messages.csv", dtype=str)
    assert list(out.columns) == INGESTED_COLUMNS
    assert len(out) == 2
    assert out["source_record_number"].tolist() == ["1", "2"]


def test_manifest_counts_and_hash(ingested):
    src, data, manifest = ingested
    assert manifest["raw_line_count"] == manifest["records_ingested"] == 2
    assert manifest["file_sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert manifest["trading_date"] == "2012-06-21"
    on_disk = json.loads((data / "processed" / "manifest.json").read_text())
    assert on_disk["batch_id"] == manifest["batch_id"]


def test_raw_copy_is_byte_identical_and_source_untouched(ingested):
    src, _, manifest = ingested
    copy = Path(manifest["lake_raw_copy"])
    assert copy.read_bytes() == src.read_bytes() == ROWS.encode()


def test_values_are_kept_as_text_not_coerced(tmp_path):
    src = tmp_path / NAME
    src.write_text("abc,1,10,,1000,1\n", encoding="utf-8")
    ingest_data(src, tmp_path / "data")
    out = pd.read_csv(tmp_path / "data" / "processed" / "ingested_messages.csv",
                      dtype=str, keep_default_na=False)
    assert out.loc[0, "time"] == "abc" and out.loc[0, "size"] == ""


def test_helpers(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"a\nb\nc\n")
    assert count_lines(f) == 3
    assert sha256_of(f) == hashlib.sha256(b"a\nb\nc\n").hexdigest()
