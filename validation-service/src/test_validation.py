
from pathlib import Path
import pandas as pd

from validate_data import validate_data

ROOT = Path(__file__).resolve().parents[2]

SOURCE_FILE = ROOT / "data" / "processed" / "transformed_messages.csv"
TEST_FILE = ROOT / "data" / "processed" / "test_messages.csv"
REPORT_FILE = ROOT / "data" / "processed" / "test_validation_report.json"


def test_invalid_records():
   
    df = pd.read_csv(SOURCE_FILE).head(5).copy()


    df.loc[df.index[0], "event_type"] = 99
    df.loc[df.index[1], "direction"] = 0

    df.to_csv(TEST_FILE, index=False)

    try:
        validate_data(TEST_FILE, REPORT_FILE)

        import json
        with open(REPORT_FILE, "r", encoding="utf-8") as file:
            report = json.load(file)

        assert report["invalid_event_types"] == 1
        assert report["invalid_normal_directions"] == 1

        print("\nTEST PASSED: Invalid records were detected.")

    finally:
        if TEST_FILE.exists():
            TEST_FILE.unlink()

        if REPORT_FILE.exists():
            REPORT_FILE.unlink()


if __name__ == "__main__":
    test_invalid_records()
