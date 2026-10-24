from datetime import datetime, timezone
from pathlib import Path
import json
import math 
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.schema import(
    HALT_EVENT_TYPE,
    RAW_COLUMNS,
    REQUIRED_LINEAGE_COLUMNS,
    SECONDS_PER_DAY,
    TRANSFORMED_COLUMNS,
    VALID_EVENT_TYPES,
)

DATA_DIR = ROOT / "data"

def _stats(frame):
    has_time = len(frame)>0 and bool(frame["time"].notna().any())
    return{
        "records":int(len(frame)),
        "sum_size": float(frame["size"].sum()),
        "min_time": float(frame["time"].min()) if has_time else None,
        "max_time": float(frame["time"].max()) if has_time else None,

    }

def _close(a,b):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)

def validate_data(data_dir=None):
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    input_file = data_dir / "processed" / "transformed_messages.csv"
    manifest_file = data_dir / "processed" / "manifest.json"
    report_file = data_dir / "processed" / "validation_report.json"
    valid_file = data_dir / "processed" / "validated_messages.csv"
    rejected_file = data_dir / "rejected" / "rejected_messages.csv"
    curated_file = data_dir / "lake" / "curated" / "validated_messages.parquet"

    for path in (input_file, manifest_file):
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    df=pd.read_csv(input_file)

    missing = [c for c in TRANSFORMED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns : {missing}")

    for column in RAW_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")


    event = df["event_type"]
    halt = event == HALT_EVENT_TYPE
    normal = ~halt

    masks = {
        "MISSING_OR_NON_NUMERIC":df[RAW_COLUMNS].isna() .any(axis=1),
        "INVALID_EVENT_TYPE": event.notna() & ~event.isin(VALID_EVENT_TYPES),
        "INVALID_TIME": (df["time"]< 0) | (df["time"] >=SECONDS_PER_DAY),
        "INVALID_SIZE": normal & (df["size"] <= 0),
        "INVALID_PRICE": normal & (df["price"] <= 0),
        "INVALID_DIRECTION": (
            normal & df["direction"].notna () & ~df["direction"].isin([-1,1])
        ),
        "INVALID_HALT_FIELDS":halt
        & (
            (df["size"] != 0)
            | (df["order_id"] != 0)
            | (df["direction"] != -1)
            | ~df["price"].isin([-1,0,1])
        ),
        "MISSING_TIMESTAMP": df["time"].notna() & df["event_timestamp"].isna(),
        "MISSING_LINEAGE": df[REQUIRED_LINEAGE_COLUMNS].isna().any(axis=1),


    }

    reason =pd.Series("", index=df.index)
    for code, mask in masks.items():
        reason = reason.where(~mask, reason + code + ";")
    reason = reason.str.rstrip(";")

    rejected_mask = reason != ""
    df["reject_reason"]=reason
    df["validation_status"]= rejected_mask.map(
        {True: "REJECTED",False:"VALID"}
    )
    df["final_destination"] =rejected_mask.map(
        {True: "rejected", False:"curated"}
    )
    df["validated_at"] = datetime.now(timezone.utc).isoformat()

    valid = df.loc[~rejected_mask].copy()
    rejected = df.loc[rejected_mask].copy()

    for path in (valid_file, rejected_file, curated_file):
        path.parent.mkdir(parents=True, exist_ok=True)

    valid.to_csv(valid_file, index=False)
    rejected.to_csv(rejected_file, index=False)

    curated = valid.copy()
    curated["event_timestamp"] = pd.to_datetime(curated["event_timestamp"])
    curated.to_parquet(curated_file, index=False)

    all_stats = _stats(df)
    valid_stats = _stats(valid)
    rejected_stats = _stats(rejected)

    n =manifest["records_ingested"]
    record_ids = pd.concat(
        [valid["source_record_number"], rejected["source_record_number"]]
    ). tolist()

    reconciliation ={
        "raw_lines_equal_ingested": manifest["raw_line_count"] == n,
        "ingested_equal_transformed": n == len(df),
        "transformed_equal_valid_plus_rejected": len(df)
        == len(valid) + len(rejected),
        "every_record_number_accounted_for_once": sorted(record_ids)
        == list(range(1, n + 1)),
        "sum_size_matches": _close(
            manifest["sum_size"],
            valid_stats["sum_size"] + rejected_stats["sum_size"],
        ),
        "min_time_matches": _close(manifest["min_time"],all_stats["min_time"]),
        "max_time_matches": _close(manifest["max_time"], all_stats["max_time"]),

    }
    reconciliation = {k: bool(v) for k, v in reconciliation.items()}

    report = {
        "batch_id":manifest["batch_id"],
        "source_file":manifest["source_file"],
        "file_sha256":manifest["file_sha256"],
        "validated_at":datetime.now(timezone.utc).isoformat(),
        "stages": {
            "raw": {"records":manifest["raw_line_count"]},
            "ingested":{
                "records": manifest["records_ingested"],
                "sum_size": manifest["sum_size"],
                "min_time": manifest["min_time"],
                "max_time": manifest["max_time"],
            },
            "transformed": all_stats,
            "valid": valid_stats,
            "rejected": rejected_stats,

        },
        "reject_reason_counts":{
            code: int(mask.sum()) for code, mask in masks.items()
        },

        "duplicate_rows_flagged": int(df["is_duplicate"].sum()),
        "reconciliation": reconciliation,
        "reconciliation_pass":all(reconciliation.values()),
        "quality_pass":bool(len(rejected)==0),
    }

    report_file.write_text(
        json.dumps(report, indent=4, default=str), encoding="utf=8"
    )

    print("VALIDATION COMPLETED")
    print("-" * 40)
    print("Transformed records:",len(df))
    print("Valid records:",len(valid))
    print("Rejected records:", len(rejected))
    print("Duplicates flagged:", report["duplicate_rows_flagged"])
    print("Reconciliation pass", report["reconciliation_pass"])
    for name, result in reconciliation.items():
        print(f" {name}:{result}")
    print("Report saved to:",report_file)

    return report

if __name__ == "__main__":
    validate_data()

        
