
"""Recompute the checklist metrics from the raw LOBSTER message CSV and
(optionally) compare them with the running backend API.

LOBSTER message columns: time, type, order_id, size, price (x10000), direction.

Usage (from the project root):
    python tests/verify_metrics.py
    python tests/verify_metrics.py --api-url http://localhost:8080 --user analyst
        (password is read from the VERIFY_PASSWORD environment variable)

Exit code 0 = every check that ran passed, 1 = at least one failed.
"""
import argparse
import base64
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DEFAULT_CSV = "data/raw/AAPL_2012-06-21_34200000_57600000_message_1.csv"

EXPECTED = {
    "rows": 118497,
    "avg_price": Decimal("583.1436"),
    "max_price": Decimal("588.22"),
    "avg_size": Decimal("85.4226"),
    "max_size": 15000,
}

# Field-name hints used to find each metric inside the API's JSON.
API_HINTS = {
    "rows": ["totalrecords", "totalrows", "rowcount", "totalmessages", "messagecount"],
    "avg_price": ["avgprice", "averageprice", "meanprice"],
    "max_price": ["maxprice", "highestprice", "highprice"],
    "avg_size": ["avgordersize", "avgsize", "averagesize", "meansize"],
    "max_size": ["maxsize", "largestsize", "largestorder"],
}


def compute_from_csv(path: Path) -> dict:
    rows = 0
    sum_price = 0
    sum_size = 0
    max_price = 0
    max_size = 0
    with path.open(newline="", encoding="utf-8") as fh:
        for rec in csv.reader(fh):
            if not rec:
                continue
            size = int(rec[3])
            price = int(rec[4])
            rows += 1
            sum_price += price
            sum_size += size
            max_price = max(max_price, price)
            max_size = max(max_size, size)
    if rows == 0:
        raise SystemExit(f"{path} has no rows")
    q = Decimal("0.0001")
    return {
        "rows": rows,
        "avg_price": (Decimal(sum_price) / rows / 10000).quantize(q, ROUND_HALF_UP),
        "max_price": Decimal(max_price) / 10000,
        "avg_size": (Decimal(sum_size) / rows).quantize(q, ROUND_HALF_UP),
        "max_size": max_size,
    }


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, list):
        pass  # lists (chart series etc.) are not scalar metrics
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[prefix.rstrip(".")] = obj
    return out


def find_in_api(flat: dict, hints: list):
    for hint in hints:  # hints are ordered most specific first
        for key, val in flat.items():
            leaf = key.split(".")[-1].lower().replace("_", "")
            if leaf == hint or hint in leaf:
                return key, val
    return None, None


def fetch_api(url: str, user: str, password: str) -> dict:
    req = urllib.request.Request(url.rstrip("/") + "/api/analytics/summary")
    if user:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def close(a, b, tol=Decimal("0.00006")) -> bool:
    return abs(Decimal(str(a)) - Decimal(str(b))) <= tol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--api-url", default=None)
    ap.add_argument("--user", default="")
    args = ap.parse_args()

    failed = 0
    path = Path(args.csv)
    if not path.exists():
        print(f"FAIL: raw CSV not found: {path}")
        return 1

    actual = compute_from_csv(path)
    print(f"== Raw CSV: {path}")
    for name, want in EXPECTED.items():
        got = actual[name]
        ok = close(got, want)
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name:10} csv={got}  checklist={want}")

    if args.api_url:
        print(f"== API: {args.api_url}/api/analytics/summary")
        try:
            data = fetch_api(args.api_url, args.user, os.environ.get("VERIFY_PASSWORD", ""))
        except (urllib.error.URLError, OSError) as exc:
            print(f"  FAIL  could not call the API: {exc}")
            return 1
        flat = flatten(data)
        print("  numeric fields returned:", ", ".join(sorted(flat)) or "(none)")
        for name, hints in API_HINTS.items():
            key, val = find_in_api(flat, hints)
            if key is None:
                print(f"  SKIP  {name:10} no matching field in the API response")
                continue
            ok = close(val, actual[name])
            failed += not ok
            print(f"  {'PASS' if ok else 'FAIL'}  {name:10} api[{key}]={val}  csv={actual[name]}")
    else:
        print("== API comparison skipped (no --api-url)")

    print("RESULT:", "FAILED" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())