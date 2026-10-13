from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "data" / "processed" / "transformed_messages.csv"
REPORT_DIR = ROOT / "data" / "processed"
REPORT_FILE = REPORT_DIR / "validation_report.json"

def validate_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    checks = {
        "file_exists": True,
        "record_count": len(df),
        "required_columns_present": all(
            column in df.columns
            for column in [
                "source_record_number",
                "time",
                "event_type",
                "order_id",
                "size",
                "price",
                "direction",
                "source_file",
                "ingestion_timestamp",
                "price_dollars",
            ]
        ),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "invalid_event_types":int(
            (~df["event_type"].isin([1,2,3,4,5])).sum()
        ),
        "invalid_sizes": int((df["size"] <= 0).sum()),
        "invalid_directions": int(
            (~df["direction"].isin([-1, 1])).sum()
        ),
        "price_conversion_errors": int(
            (df["price_dollars"] !=df["price"] / 10000).sum()
        ),

        "missing_source_file": int(df["source_file"].isna().sum()),
        "missing_source_record_number": int(
            df["source_record_number"].isna().sum()
        ),
    }

    checks["overall_pass"] = (
        checks["required_columns_present"]
        and checks["missing_values"] == 0
        and checks["invalid_event_types"] == 0
        and checks["invalid_directions"] == 0
        and checks["invalid_sizes"] == 0
        and checks["price_conversion_errors"] == 0
        and checks["missing_source_file"] == 0
        and checks["missing_source_record_number"] == 0
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(checks, file, indent=4)


    print("VALIDATION COMPLETED")
    print("-" * 35)

    for name, result in checks.items():
        print(f"{name}: {result}")

    print("Report saved to:", REPORT_FILE)

if __name__ == "__main__":
    validate_data()
