from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for s in ("ingestion-service", "transformation-service"):
    sys.path.insert(0, str(ROOT / s / "src"))

from ingest import ingest_data
from transform import transform_data
from common.schema import TRANSFORMED_COLUMNS

NAME = "T_2012-06-21_34200000_57600000_message_1.csv"


def run(tmp_path, rows):
    src = tmp_path / NAME
    src.write_text("\n".join(rows) + "\n", encoding="utf-8")
    data = tmp_path / "data"
    ingest_data(src, data)
    summary = transform_data(data)
    return summary, pd.read_csv(data / "processed" / "transformed_messages.csv")


def test_missing_input_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        transform_data(tmp_path)


def test_row_count_is_preserved_and_columns_match(tmp_path):
    summary, out = run(tmp_path, ["34200.0,1,1,10,1000000,1"] * 4)
    assert summary["records_in"] == summary["records_out"] == len(out) == 4
    assert list(out.columns) == TRANSFORMED_COLUMNS


def test_price_scaled_and_timestamp_built(tmp_path):
    _, out = run(tmp_path, ["34200.5,1,1,10,5853300,1"])
    assert out.loc[0, "price_dollars"] == 585.33
    assert str(out.loc[0, "event_timestamp"]).startswith("2012-06-21 09:30:00.5")


@pytest.mark.parametrize("code,label", [(1, "SUBMIT"), (2, "CANCEL_PARTIAL"), (3, "DELETE"),
                                        (4, "EXECUTE_VISIBLE"), (5, "EXECUTE_HIDDEN"),
                                        (6, "CROSS_TRADE"), (7, "HALT"), (9, "UNKNOWN")])
def test_event_labels(tmp_path, code, label):
    _, out = run(tmp_path, [f"34200.0,{code},1,10,1000,1"])
    assert out.loc[0, "event_label"] == label


def test_duplicates_flagged_first_kept(tmp_path):
    summary, out = run(tmp_path, ["34200.0,1,1,10,1000,1"] * 3 + ["34200.1,1,2,10,1000,1"])
    assert out["is_duplicate"].tolist() == [False, True, True, False]
    assert summary["duplicates_flagged"] == 2


def test_bad_numbers_become_nan_not_crashes(tmp_path):
    _, out = run(tmp_path, ["abc,1,1,10,1000,1"])
    assert pd.isna(out.loc[0, "time"]) and pd.isna(out.loc[0, "event_timestamp"])


def test_lineage_and_version_columns_filled(tmp_path):
    _, out = run(tmp_path, ["34200.0,1,1,10,1000,1"])
    for c in ("source_file", "file_sha256", "batch_id", "pipeline_version", "transformations_applied"):
        assert out[c].notna().all()
