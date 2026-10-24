from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys

import pandas as pd

ROOT = Path(__file__) .resolve() .parents[2]
sys.path.insert(0, str(ROOT))

from common.schema import INGESTED_COLUMNS, RAW_COLUMNS

DATA_DIR =ROOT / "data"
DEFAULT_INPUT = (
    DATA_DIR / "raw" / "AAPL_2012-06-21_34200000_57600000_message_1.csv"  
)

def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b"") :
            digest.update(block)
        return digest.hexdigest()

def count_lines(path):
    with open(path, "rb") as file:
        return sum(1 for _ in file)

def ingest_data(input_file=None, data_dir=None):
    input_file = Path(input_file) if input_file else DEFAULT_INPUT
    data_dir = Path(data_dir) if data_dir else DATA_DIR

    if not input_file.exists():
        raise FileNotFoundError (f" Input dataset not found: {input_file}")

    file_hash =sha256_of(input_file)
    now = datetime.now(timezone.utc)
    batch_id = f"{now:%Y%m%dT%H%M%SZ}_{file_hash[:8] }"

    lake_raw_dir = data_dir / "lake" / "raw" / batch_id
    lake_raw_dir.mkdir(parents=True, exist_ok=True)
    raw_copy = lake_raw_dir / input_file.name
    shutil.copy2(input_file, raw_copy)
    if sha256_of(raw_copy) != file_hash:
        raise RuntimeError("Raw copy hash does not match the source file")


    df = pd.read_csv(
        input_file,
        header =None,
        names = RAW_COLUMNS,
        dtype =str,
        keep_default_na=False,
    ) .fillna("")

    match = re.search(r"(\d{4}-\d{2}-\d{2})", input_file.name)
    trading_date = match.group(1) if match else ""

    df.insert(0, "source_record_number", range(1, len(df)+1))
    df["source_file"] = input_file.name
    df["trading_date"] = trading_date
    df["file_sha256"] = file_hash
    df["batch_id"] = batch_id
    df["ingestion_timestamp"] = now.isoformat()
    df = df[INGESTED_COLUMNS]

    size_num = pd.to_numeric(df["size"].str.strip(), errors="coerce")
    time_num = pd.to_numeric(df["time"].str.strip(), errors="coerce")
    has_time = bool(time_num.notna().any())

    manifest = {
        "batch_id": batch_id,
        "source_file":input_file.name,
        "file_sha256": file_hash,
        "file_size_bytes": input_file.stat().st_size,
        "trading_date": trading_date,
        "raw_line_count": count_lines(input_file),
        "records_ingested":int(len(df)),
        "sum_size": float(size_num.sum()),
        "min_time": float(time_num.min()) if has_time else None,
        "max_time": float(time_num.max()) if has_time else None,
        "lake_raw_copy": str(raw_copy),
        "ingested_at": now.isoformat(),
    }

    out_dir = data_dir /"processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file =out_dir / "ingested_messages.csv"
    df.to_csv(output_file, index=False)

    manifest_text =json.dumps(manifest, indent=4)
    (out_dir / "manifest.json"). write_text(manifest_text, encoding = "utf-8")
    (lake_raw_dir / "manifest.json") .write_text(manifest_text, encoding= "utf-8")

    print("INGESTION COMPLETED")
    print("-" * 40)
    print("Batch ID:", batch_id)
    print("Source file:", input_file.name)
    print("SHA-256:",file_hash )
    print("Raw lines:",manifest["raw_line_count"] )
    print("Records ingested:", len(df))
    print("Raw copy:", raw_copy)
    print("Output file:", output_file)

    return manifest

if __name__=="__main__":
    ingest_data()
    
    
        