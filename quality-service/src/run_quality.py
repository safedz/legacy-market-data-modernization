
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import pandas as pd

from common.schema import PIPELINE_VERSION
from lifecycle_checks import lifecycle_checks
from orderbook_reconcile import reconcile_files
from profile_data import profile
from run_manifest import build_run_manifest

DATA_DIR = ROOT / "data"


def find_orderbook(data_dir, source_file, explicit=None):
    if explicit:
        return Path(explicit)
    return Path(data_dir) / "raw" / source_file.replace("_message_", "_orderbook_")


def run_quality(data_dir=None, orderbook_file=None, min_match_rate=0.99, strict=False):
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    processed = data_dir / "processed"
    validated = processed / "validated_messages.csv"
    manifest_file = processed / "manifest.json"
    for p in (validated, manifest_file):
        if not p.exists():
            raise FileNotFoundError(f"Run the pipeline first, missing: {p}")

    ingest_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    messages = pd.read_csv(validated)

    book_path = find_orderbook(data_dir, ingest_manifest["source_file"], orderbook_file)
    if book_path.exists():
        recon = reconcile_files(validated, book_path, min_match_rate)
        recon["status"] = "PASS" if recon["pass"] else "FAIL"
    else:
        recon = {"status": "SKIPPED", "pass": None,
                 "reason": f"orderbook file not found: {book_path}"}

    lifecycle = lifecycle_checks(messages)
    prof = profile(messages)

    gates = {
        "orderbook_reconciliation": recon["status"],
        "order_lifecycle": "PASS" if lifecycle["pass"] else "WARN",
    }
    quality = {
        "batch_id": ingest_manifest["batch_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "orderbook_reconciliation": recon,
        "order_lifecycle": lifecycle,
        "gates": gates,
        "overall_pass": recon["status"] != "FAIL" and (lifecycle["pass"] or not strict),
    }

    (processed / "quality_report.json").write_text(
        json.dumps(quality, indent=4, default=str), encoding="utf-8")
    (processed / "profile_report.json").write_text(
        json.dumps(prof, indent=4, default=str), encoding="utf-8")

    run_manifest = build_run_manifest(
        data_dir,
        extra_inputs=[ingest_manifest.get("lake_raw_copy"),
                      book_path if book_path.exists() else None],
        pipeline_version=PIPELINE_VERSION,
        gates=gates,
    )
    (processed / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=4), encoding="utf-8")

    print("QUALITY CHECKS COMPLETED")
    print("-" * 40)
    if recon["status"] == "SKIPPED":
        print("Order book reconciliation: SKIPPED -", recon["reason"])
    else:
        rate = recon["match_rate"]
        print(f"Order book reconciliation: {recon['status']} "
              f"(checked {recon['checked']}, matched {recon['matched']}, "
              f"mismatched {recon['mismatched']}, "
              f"match rate {rate:.4%}, coverage {recon['coverage']:.1%})")
    print(f"Order lifecycle: {gates['order_lifecycle']} "
          f"(orphan events {lifecycle['orphan_events']}, informational)")
    for name, count in lifecycle["violations"].items():
        if count:
            print(f"  violation {name}: {count}")
    print("Reports saved to:", processed)
    return quality


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Pearl Protocol quality stage")
    ap.add_argument("--orderbook")
    ap.add_argument("--min-match-rate", type=float, default=0.99)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    q = run_quality(orderbook_file=a.orderbook, min_match_rate=a.min_match_rate, strict=a.strict)
    sys.exit(0 if q["overall_pass"] else 1)
