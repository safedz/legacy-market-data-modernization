from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
for service in ("ingestion-service", "transformation-service",
                "validation-service", "quality-service", "surveillance"):
    sys.path.insert(0, str(ROOT / service / "src"))

from ingest import ingest_data
from transform import transform_data
from validate_data import validate_data
from run_quality import run_quality
from detect import run_surveillance


def main():
    parser = argparse.ArgumentParser(description="Pearl Protocol pipeline")
    parser.add_argument("--input", help="path to a LOBSTER message CSV")
    parser.add_argument("--orderbook", help="path to the matching LOBSTER orderbook CSV")
    parser.add_argument("--skip-quality", action="store_true",
                        help="skip the quality stage")
    parser.add_argument("--skip-surveillance", action="store_true",
                        help="skip the surveillance stage")
    parser.add_argument("--strict", action="store_true",
                        help="also fail the run on order lifecycle violations")
    parser.add_argument("--min-match-rate", type=float, default=0.99,
                        help="minimum order book reconciliation match rate")
    args = parser.parse_args()

    ingest_data(args.input)
    print()
    transform_data()
    print()
    report = validate_data()

    if not report["reconciliation_pass"]:
        print("\nRECONCILIATION FAILED - see validation_report.json")
        sys.exit(1)

    if not args.skip_quality:
        print()
        quality = run_quality(orderbook_file=args.orderbook,
                              min_match_rate=args.min_match_rate, strict=args.strict)
        if not quality["overall_pass"]:
            print("\nQUALITY GATE FAILED - see quality_report.json")
            sys.exit(1)

    
    if not args.skip_surveillance:
        print()
        run_surveillance()

    print("\nPIPELINE OK")


if __name__ == "__main__":
    main()