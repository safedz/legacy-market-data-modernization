"""Read the data lake back from Cloudflare R2: list a batch, download and verify it, and query the
curated Parquet file in place with DuckDB.

    python deployment/cloud/r2_lake.py list                       # objects of the newest batch
    python deployment/cloud/r2_lake.py verify                     # download + check every SHA-256
    python deployment/cloud/r2_lake.py query summary              # DuckDB over r2, JSON output
    python deployment/cloud/r2_lake.py query event-counts --batch 20261119T181327Z_bd672f66

Uses the same variables as the upload: R2_ACCOUNT_ID  R2_ACCESS_KEY_ID  R2_SECRET_ACCESS_KEY  R2_BUCKET
`query` also needs:  pip install duckdb
It keeps DuckDB's httpfs extension in <project>/duckdb_extensions (override with DUCKDB_EXTENSION_DIR).
"""
from pathlib import Path
import argparse
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from upload_to_r2 import have_credentials, make_client, sha256_of  # noqa: E402

ZONES = ("raw", "curated", "rejected", "reports")
BATCH_RE = re.compile(r"^\d{8}T\d{6}Z_[0-9a-f]{8}$")
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


QUERIES = {
    "summary": "SELECT count(*) AS records, round(avg(price_dollars), 4) AS avg_price, "
               "max(price_dollars) AS max_price, round(avg(size), 4) AS avg_order_size, "
               "max(size) AS largest_order FROM read_parquet('{p}')",
    "event-counts": "SELECT event_label, count(*) AS messages FROM read_parquet('{p}') "
                    "GROUP BY 1 ORDER BY 2 DESC",
    "price-range": "SELECT min(price_dollars) AS min_price, max(price_dollars) AS max_price, "
                   "avg(price_dollars) AS avg_price FROM read_parquet('{p}')",
}


def list_objects(client, bucket, prefix):
    """All keys under a prefix, following pagination."""
    keys, token = [], None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = client.list_objects_v2(**kwargs)
        keys += [o["Key"] for o in resp.get("Contents", [])]
        if not resp.get("IsTruncated"):
            return keys
        token = resp["NextContinuationToken"]


def latest_batch(client, bucket):
    """Newest batch id under raw/. Batch ids start with a UTC timestamp, so they sort by time."""
    batches = set()
    for key in list_objects(client, bucket, "raw/"):
        parts = key.split("/")
        if len(parts) >= 3 and BATCH_RE.match(parts[1]):
            batches.add(parts[1])
    if not batches:
        raise LookupError("No batches found in the bucket (nothing under raw/). Upload one first.")
    return max(batches)


def batch_keys(client, bucket, batch):
    keys = []
    for zone in ZONES:
        keys += list_objects(client, bucket, f"{zone}/{batch}/")
    return keys


def download_and_verify(client, bucket, batch, out_dir):
    """Download every object of a batch and compare its SHA-256 with the one stored at upload time."""
    results = []
    for key in batch_keys(client, bucket, batch):
        dest = Path(out_dir) / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, key, str(dest))
        actual = sha256_of(dest)
        expected = client.head_object(Bucket=bucket, Key=key).get("Metadata", {}).get("sha256")
        results.append({"key": key, "bytes": dest.stat().st_size, "sha256": actual,
                        "verified": expected == actual})
    return results


def check_against_manifest(out_dir, batch):
    """The raw object must hash to the SHA-256 the pipeline recorded when it first read the file."""
    manifest_path = Path(out_dir) / "reports" / batch / "manifest.json"
    if not manifest_path.exists():
        return {"checked": False, "reason": "no manifest.json in this batch"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = Path(out_dir) / "raw" / batch / manifest["source_file"]
    ok = raw.exists() and sha256_of(raw) == manifest["file_sha256"]
    return {"checked": True, "ok": ok, "expected": manifest["file_sha256"], "file": manifest["source_file"]}


def build_query(name, bucket, batch):
    if name not in QUERIES:
        raise ValueError(f"Unknown query '{name}'. Choose one of: {', '.join(QUERIES)}")
    if not BATCH_RE.match(batch):
        raise ValueError(f"Invalid batch id: {batch!r}")
    if not BUCKET_RE.match(bucket):
        raise ValueError(f"Invalid bucket name: {bucket!r}")
    return QUERIES[name].format(p=f"s3://{bucket}/curated/{batch}/validated_messages.parquet")


def extension_dir(env=os.environ):
    """Writable folder for DuckDB's httpfs extension. Defaults to <project>/duckdb_extensions so it
    works even when the user's home folder is locked down."""
    return Path(env.get("DUCKDB_EXTENSION_DIR") or Path(__file__).resolve().parents[2] / "duckdb_extensions")


def query_r2(name, batch, env=os.environ):
    """Run one fixed query on the curated Parquet file directly in R2 (nothing is downloaded)."""
    sql = build_query(name, env["R2_BUCKET"], batch)
    import duckdb  # imported late so list/verify need no extra package

    def lit(value):
        return "'" + value.replace("'", "''") + "'"

    con = duckdb.connect()
    folder = extension_dir(env)
    folder.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET extension_directory = {lit(folder.as_posix())}")
    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")
    con.execute(
        "CREATE SECRET r2_lake (TYPE S3, "
        f"KEY_ID {lit(env['R2_ACCESS_KEY_ID'])}, SECRET {lit(env['R2_SECRET_ACCESS_KEY'])}, "
        f"ENDPOINT {lit(env['R2_ACCOUNT_ID'] + '.r2.cloudflarestorage.com')}, "
        "URL_STYLE 'path', REGION 'auto')")
    cur = con.execute(sql)
    columns = [d[0] for d in cur.description]
    return {"query": name, "batch": batch, "columns": columns, "rows": cur.fetchall()}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read the lake back from Cloudflare R2")
    ap.add_argument("command", choices=["list", "verify", "query"])
    ap.add_argument("name", nargs="?", help="query name (for 'query'): " + ", ".join(QUERIES))
    ap.add_argument("--batch", help="batch id (default: newest in the bucket)")
    ap.add_argument("--out", help="download folder for 'verify' (default: a temporary folder)")
    args = ap.parse_args(argv)

    if not have_credentials():
        print("Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET first.",
              file=sys.stderr)
        return 2
    bucket = os.environ["R2_BUCKET"]
    client = make_client()
    batch = args.batch or latest_batch(client, bucket)
    if not BATCH_RE.match(batch):
        print(f"Invalid batch id: {batch!r}", file=sys.stderr)
        return 2

    if args.command == "list":
        print(f"Batch {batch} in bucket {bucket}:")
        for key in batch_keys(client, bucket, batch):
            print(f"  {key}")
        return 0

    if args.command == "verify":
        out = args.out or tempfile.mkdtemp(prefix="r2_verify_")
        results = download_and_verify(client, bucket, batch, out)
        for r in results:
            print(f"  {'OK ' if r['verified'] else 'BAD'} {r['key']}  sha256={r['sha256'][:12]}")
        manifest = check_against_manifest(out, batch)
        if manifest["checked"]:
            print(f"  {'OK ' if manifest['ok'] else 'BAD'} raw file matches the SHA-256 recorded at ingestion")
        else:
            print(f"  SKIP manifest check ({manifest['reason']})")
        good = bool(results) and all(r["verified"] for r in results) and manifest.get("ok", True)
        print(f"Downloaded {len(results)} objects to {out}")
        print("VERIFIED" if good else "VERIFICATION FAILED")
        return 0 if good else 1

    if not args.name:
        print("Give a query name: " + ", ".join(QUERIES), file=sys.stderr)
        return 2
    print(json.dumps(query_r2(args.name, batch), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
