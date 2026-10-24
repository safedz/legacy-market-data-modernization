from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
for service in ("ingestion-service", "transformation-service", "validation-service"):
    sys.path.insert(0, str(ROOT / service / "src"))

from ingest import ingest_data
from transform import transform_data
from validate_data import validate_data

def main():
    parser = argparse.ArgumentParser(description="Pearl Protocol pipeline")
    parser.add_argument("--input", help="path to a LOBSTER message CSV")
    args = parser.parse_args()

    ingest_data(args.input)
    print()
    transform_data()
    print()
    report = validate_data()

    if not report["reconciliation_pass"]:
        print("\nRECONCILIATION FAILED - see validation_report.json")
        sys.exit(1)
    print("\nPIPELINE OK")


if __name__ == "__main__":
    main()