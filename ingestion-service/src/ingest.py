from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE=(
    ROOT / "data" / "raw" /
    "AAPL_2012-06-21_34200000_57600000_message_1.csv"

)

OUTPUT_DIR =ROOT / "data" / "processed"
OUTPUT_FILE =OUTPUT_DIR / "ingested_messages.csv"

COLUMNS=[
    "time",
    "event_type",
    "order_id",
    "size",
    "price",
    "direction",
]

def ingest_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    df =pd.read_csv(INPUT_FILE,header=None, names=COLUMNS)

    df.insert(
        0,
        "source_record_number",
        range(1, len(df) + 1)
    )

    df["source_file"]= INPUT_FILE.name
    df["ingestion_timestamp"] = datetime.now(
        timezone.utc
    ).isoformat()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_FILE, index=False)

    print("INGESTION COMPLETED")
    print("-"*40)
    print("Source file:",INPUT_FILE.name)
    print("Records ingested:", len(df))
    print("Output file:",OUTPUT_FILE)
    print("Output columns:",len(df.columns))

if __name__=="__main__":
    ingest_data()
        
