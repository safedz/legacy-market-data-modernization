from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from common.schema import(
    BUSINESS_COLUMNS,
    EVENT_LABELS,
    INGESTED_COLUMNS,
    PIPELINE_VERSION,
    PRICE_SCALE,
    RAW_COLUMNS,
    TRANSFORMED_COLUMNS,

)

DATA_DIR = ROOT / "data"

TRANSFORMATIONS = (
    "trim; type_cast; timestamp_built; price_scaled;"
    "event_labelled; duplicate_flagged"
)

def transform_data(data_dir=None):
    data_dir =Path(data_dir) if data_dir else DATA_DIR
    input_file = data_dir / "processed" / "ingested_messages.csv"
    output_file = data_dir / "processed" / "transformed_messages.csv"

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    df =pd.read_csv(input_file, dtype=str, keep_default_na=False)
    original_count= len(df)

    missing = [c for c in INGESTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


    for column in df.columns:
        df[column] = df[column].str.strip()


    for column in RAW_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["source_record_number"] = pd.to_numeric(
        df["source_record_number"]
    ) .astype("int64")

    df["price_dollars"] =(df['price'] / PRICE_SCALE).round(4)

    trading_day = pd.to_datetime(df["trading_date"], errors="coerce")
    df["event_timestamp"] = trading_day + pd. to_timedelta(
        df["time"], unit="s"
    )

    df["event_label"] = df["event_type"].map(EVENT_LABELS).fillna("UNKNOWN")

    df["is_duplicate"] = df.duplicated(subset=BUSINESS_COLUMNS, keep="first" )

    df["pipeline_version"]=PIPELINE_VERSION
    df["transformations_applied"] = TRANSFORMATIONS
    df["transformed_at"] = datetime.now(timezone.utc).isoformat()

    df =df[TRANSFORMED_COLUMNS]

    if len(df) != original_count:
        raise RuntimeError("Transformation changed the row count")

    df.to_csv(output_file, index=False)

    print("TRANSFORMATION COMPLETED")
    print("-" * 40)
    print("Input records:", original_count)
    print("Output records:", len(df))
    print("Duplicates flagged:", int(df["is_duplicate"].sum()))
    print("Output file:", output_file)

    return {
        "records_in": original_count,
        "records_out": int(len(df)),
        "duplicates_flagged": int(df["is_duplicate"].sum()),
    }

if __name__ == "__main__":
    transform_data()

