"""Upload the latest pipeline batch to Cloudflare R2 (S3-compatible object storage).

Layout in the bucket:
    raw/<batch_id>/<message file>        original input, byte-for-byte
    curated/<batch_id>/validated_messages.parquet
    rejected/<batch_id>/rejected_messages.csv   quarantine zone: every record that failed validation
    reports/<batch_id>/*.json            manifest, validation, quality, profile, run manifest
Every object carries its SHA-256 as metadata and is checked after upload.

Credentials come from environment variables (never put them in git):
    R2_ACCOUNT_ID  R2_ACCESS_KEY_ID  R2_SECRET_ACCESS_KEY  R2_BUCKET
Without them the script prints what it WOULD upload and exits 0 (safe in CI and demos).

    pip install -r deployment/cloud/requirements-cloud.txt
    python deployment/cloud/upload_to_r2.py            # upload (or dry run if no credentials)
    python deployment/cloud/upload_to_r2.py --dry-run  # always just list
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ("manifest.json", "validation_report.json", "quality_report.json",
           "profile_report.json", "run_manifest.json")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan_uploads(data_dir):
    """Return [(local_path, object_key)] for the latest batch."""
    data_dir = Path(data_dir)
    manifest_path = data_dir / "processed" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest at {manifest_path} - run the pipeline first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    batch = manifest["batch_id"]

    items = []
    raw_copy = Path(manifest["lake_raw_copy"])
    if not raw_copy.exists():  # manifest may have been produced on another machine / container
        raw_copy = data_dir / "lake" / "raw" / batch / manifest["source_file"]
    items.append((raw_copy, f"raw/{batch}/{manifest['source_file']}"))
    curated = data_dir / "lake" / "curated" / "validated_messages.parquet"
    if curated.exists():
        items.append((curated, f"curated/{batch}/validated_messages.parquet"))
    rejected = data_dir / "rejected" / "rejected_messages.csv"
    if rejected.exists():
        items.append((rejected, f"rejected/{batch}/rejected_messages.csv"))
    for name in REPORTS:
        p = data_dir / "processed" / name
        if p.exists():
            items.append((p, f"reports/{batch}/{name}"))
    missing = [str(p) for p, _ in items if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Files to upload are missing: {missing}")
    return items


def upload_batch(client, bucket, items):
    """Upload and verify each object. Returns a list of result dicts."""
    results = []
    for path, key in items:
        digest = sha256_of(path)
        client.upload_file(str(path), bucket, key, ExtraArgs={"Metadata": {"sha256": digest}})
        head = client.head_object(Bucket=bucket, Key=key)
        ok = head["ContentLength"] == path.stat().st_size and \
            head.get("Metadata", {}).get("sha256") == digest
        results.append({"key": key, "bytes": path.stat().st_size, "sha256": digest, "verified": ok})
    return results


def make_client(env=os.environ):
    import boto3  

    return boto3.client(
        "s3",
        endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def have_credentials(env=os.environ):
    return all(env.get(k) for k in
               ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Upload latest batch to Cloudflare R2")
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    items = plan_uploads(args.data_dir)
    if args.dry_run or not have_credentials():
        why = "dry run requested" if args.dry_run else "R2_* environment variables not set"
        print(f"DRY RUN ({why}). Would upload:")
        for path, key in items:
            print(f"  {key}  ({path.stat().st_size:,} bytes)")
        return 0

    results = upload_batch(make_client(), os.environ["R2_BUCKET"], items)
    for r in results:
        print(f"  {'OK ' if r['verified'] else 'BAD'} {r['key']}  sha256={r['sha256'][:12]}")
    if not all(r["verified"] for r in results):
        print("UPLOAD VERIFICATION FAILED", file=sys.stderr)
        return 1
    print(f"Uploaded and verified {len(results)} objects to bucket {os.environ['R2_BUCKET']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
