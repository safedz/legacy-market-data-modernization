
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "data" / "processed" / "transformed_messages.csv"
REPORT_DIR = ROOT / "data" / "processed"
REPORT_FILE = REPORT_DIR / "validation_report.json"


def validate_data(input_file=None, report_file=None):
    input_file = input_file or INPUT_FILE
    report_file = report_file or REPORT_FILE
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    df = pd.read_csv(input_file)

    required_columns = [
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

    required_columns_present = all(
        column in df.columns for column in required_columns
    )

    checks = {
        "file_exists": True,
        "record_count": len(df),
        "required_columns_present": required_columns_present,
    }

    if required_columns_present:
        
        checks["invalid_event_types"] = int(
            (~df["event_type"].isin([1, 2, 3, 4, 5, 7])).sum()
        )

       
        halt = df["event_type"] == 7
        normal = ~halt

        checks["invalid_normal_sizes"] = int(
            (df.loc[normal, "size"] <= 0).sum()
        )

        checks["invalid_normal_directions"] = int(
            (~df.loc[normal, "direction"].isin([-1, 1])).sum()
        )

        
        checks["invalid_halt_fields"] = int(
            (
                halt
                & (
                    (df["size"] != 0)
                    | (df["direction"] != -1)
                    | (~df["price"].isin([-1, 0, 1]))
                    | (df["order_id"] != 0)
                )
            ).sum()
        )

        checks["invalid_times"] = int(
            ((df["time"] < 0) | ~df["time"].notna()).sum()
        )

        checks["price_conversion_errors"] = int(
            (
                (df["price_dollars"] - df["price"] / 10000).abs()
                > 1e-9
            ).sum()
        )

        checks["missing_values"] = int(df[required_columns].isna().sum().sum())
        checks["duplicate_rows"] = int(df.duplicated().sum())
        checks["missing_source_file"] = int(df["source_file"].isna().sum())
        checks["missing_source_record_number"] = int(
            df["source_record_number"].isna().sum()
        )

        checks["overall_pass"] = (
            checks["invalid_event_types"] == 0
            and checks["invalid_normal_sizes"] == 0
            and checks["invalid_normal_directions"] == 0
            and checks["invalid_halt_fields"] == 0
            and checks["invalid_times"] == 0
            and checks["price_conversion_errors"] == 0
            and checks["missing_values"] == 0
            and checks["missing_source_file"] == 0
            and checks["missing_source_record_number"] == 0
        )
    else:
        checks["overall_pass"] = False

    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as file:
        json.dump(checks, file, indent=4)

    print("VALIDATION COMPLETED")
    print("-" * 35)

    for name, result in checks.items():
        print(f"{name}: {result}")

    print("Report saved to:", report_file)


if __name__ == "__main__":
    validate_data()
