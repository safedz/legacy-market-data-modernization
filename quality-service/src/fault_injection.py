
from pathlib import Path
import argparse
import random
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (ROOT, HERE, *(ROOT / s / "src" for s in
          ("ingestion-service", "transformation-service", "validation-service"))):
    sys.path.insert(0, str(p))

import pandas as pd


FAULTS = {
    "zero_size": (3, "0", "INVALID_SIZE"),
    "unknown_event_type": (1, "9", "INVALID_EVENT_TYPE"),
    "negative_price": (4, "-5", "INVALID_PRICE"),
    "bad_direction": (5, "0", "INVALID_DIRECTION"),
    "time_not_a_number": (0, "abc", "MISSING_OR_NON_NUMERIC"),
    "time_past_midnight": (0, "90000.0", "INVALID_TIME"),
}


def inject_faults(source_csv, target_csv, per_fault=3, seed=42):
    """Write a corrupted copy. Returns {source_record_number: expected_code}."""
    lines = Path(source_csv).read_text(encoding="utf-8").splitlines()
    rng = random.Random(seed)
    eligible = [i for i, line in enumerate(lines)
                if line.split(",")[1] in ("1", "2", "3", "4") and float(line.split(",")[3]) > 0]
    rng.shuffle(eligible)
    expected, cursor = {}, 0
    for fault, (col, value, code) in FAULTS.items():
        for _ in range(per_fault):
            if cursor >= len(eligible):
                break
            idx = eligible[cursor]
            cursor += 1
            parts = lines[idx].split(",")
            parts[col] = value
            lines[idx] = ",".join(parts)
            expected[idx + 1] = code
    Path(target_csv).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return expected


def run_fault_injection(source_csv, work_dir=None, per_fault=3, seed=42):
    from ingest import ingest_data
    from transform import transform_data
    from validate_data import validate_data

    work = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="fault_"))
    work.mkdir(parents=True, exist_ok=True)
    corrupted = work / Path(source_csv).name
    expected = inject_faults(source_csv, corrupted, per_fault, seed)

    data_dir = work / "data"
    ingest_data(corrupted, data_dir)
    transform_data(data_dir)
    report = validate_data(data_dir)

    rejected = pd.read_csv(data_dir / "rejected" / "rejected_messages.csv")
    observed = dict(zip(rejected["source_record_number"], rejected["reject_reason"]))

    missed = sorted(set(expected) - set(observed))
    unexpected = sorted(set(observed) - set(expected))
    wrong_reason = sorted(r for r in expected if r in observed and expected[r] not in observed[r])

    return {
        "injected": len(expected),
        "rejected": len(observed),
        "missed_faults": missed,
        "unexpected_rejections": unexpected,
        "wrong_reason": wrong_reason,
        "reconciliation_pass": report["reconciliation_pass"],
        "pass": not (missed or unexpected or wrong_reason) and report["reconciliation_pass"],
        "work_dir": str(work),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pearl Protocol fault injection")
    ap.add_argument("--input", required=True)
    ap.add_argument("--per-fault", type=int, default=3)
    a = ap.parse_args()
    result = run_fault_injection(a.input, per_fault=a.per_fault)
    print("\nFAULT INJECTION", "PASSED" if result["pass"] else "FAILED")
    for k, v in result.items():
        print(f"  {k}: {v}")
    sys.exit(0 if result["pass"] else 1)
