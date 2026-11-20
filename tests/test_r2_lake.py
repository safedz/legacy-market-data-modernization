"""Tests for the R2 zones, read-back and verification. They use an in-memory fake of R2, so they need
neither a Cloudflare account nor the full pipeline."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment" / "cloud"))

import r2_lake  
import upload_to_r2 as up  

BATCH = "20261119T181327Z_bd672f66"
RAW_BYTES = b"34200.004241176,1,16113575,18,5853300,1\n"


class FakeR2:
    def __init__(self, page_size=1000):
        self.store, self.page = {}, page_size

    def upload_file(self, path, bucket, key, ExtraArgs=None):
        self.store[(bucket, key)] = (Path(path).read_bytes(), dict((ExtraArgs or {}).get("Metadata", {})))

    def head_object(self, Bucket, Key):
        data, meta = self.store[(Bucket, Key)]
        return {"ContentLength": len(data), "Metadata": meta}

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):
        keys = sorted(k for b, k in self.store if b == Bucket and k.startswith(Prefix))
        start = int(ContinuationToken or 0)
        page = keys[start:start + self.page]
        resp = {"Contents": [{"Key": k} for k in page]}
        if start + self.page < len(keys):
            resp.update(IsTruncated=True, NextContinuationToken=str(start + self.page))
        return resp

    def download_file(self, bucket, key, dest):
        Path(dest).write_bytes(self.store[(bucket, key)][0])


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    (d / "processed").mkdir(parents=True)
    (d / "lake" / "raw" / BATCH).mkdir(parents=True)
    (d / "lake" / "curated").mkdir(parents=True)
    (d / "rejected").mkdir()
    name = "AAPL_message_1.csv"
    raw = d / "lake" / "raw" / BATCH / name
    raw.write_bytes(RAW_BYTES)
    (d / "lake" / "curated" / "validated_messages.parquet").write_bytes(b"PAR1-demo")
    (d / "rejected" / "rejected_messages.csv").write_text("source_record_number,reject_reason\n7,INVALID_PRICE\n")
    manifest = {"batch_id": BATCH, "source_file": name, "file_sha256": hashlib.sha256(RAW_BYTES).hexdigest(),
                "lake_raw_copy": str(raw)}
    (d / "processed" / "manifest.json").write_text(json.dumps(manifest))
    for report in ("validation_report.json", "quality_report.json"):
        (d / "processed" / report).write_text("{}")
    return d


@pytest.fixture
def uploaded(data_dir):
    client = FakeR2()
    up.upload_batch(client, "bucket", up.plan_uploads(data_dir))
    return client


def test_plan_includes_rejected_quarantine_zone(data_dir):
    keys = [k for _, k in up.plan_uploads(data_dir)]
    assert f"rejected/{BATCH}/rejected_messages.csv" in keys
    assert any(k.startswith("raw/") for k in keys) and any(k.startswith("curated/") for k in keys)


def test_plan_without_rejected_file_still_works(data_dir):
    (data_dir / "rejected" / "rejected_messages.csv").unlink()
    assert not any(k.startswith("rejected/") for _, k in up.plan_uploads(data_dir))


def test_latest_batch_picks_the_newest(uploaded, data_dir):
    older = "20260101T000000Z_aaaaaaaa"
    uploaded.store[("bucket", f"raw/{older}/x.csv")] = (b"x", {})
    assert r2_lake.latest_batch(uploaded, "bucket") == BATCH


def test_latest_batch_on_empty_bucket_is_a_clear_error():
    with pytest.raises(LookupError):
        r2_lake.latest_batch(FakeR2(), "bucket")


def test_listing_follows_pagination(uploaded):
    uploaded.page = 2
    keys = r2_lake.batch_keys(uploaded, "bucket", BATCH)
    assert len(keys) == 6 and len(set(keys)) == 6  # raw, curated, rejected + 3 reports


def test_download_verifies_every_object(uploaded, tmp_path):
    results = r2_lake.download_and_verify(uploaded, "bucket", BATCH, tmp_path / "out")
    assert len(results) == 6 and all(r["verified"] for r in results)
    assert (tmp_path / "out" / "raw" / BATCH / "AAPL_message_1.csv").read_bytes() == RAW_BYTES


def test_tampered_object_is_detected(uploaded, tmp_path):
    key = ("bucket", f"curated/{BATCH}/validated_messages.parquet")
    _, meta = uploaded.store[key]
    uploaded.store[key] = (b"tampered", meta)
    results = r2_lake.download_and_verify(uploaded, "bucket", BATCH, tmp_path / "out")
    bad = [r["key"] for r in results if not r["verified"]]
    assert bad == [f"curated/{BATCH}/validated_messages.parquet"]


def test_raw_object_matches_the_hash_recorded_at_ingestion(uploaded, tmp_path):
    r2_lake.download_and_verify(uploaded, "bucket", BATCH, tmp_path / "out")
    assert r2_lake.check_against_manifest(tmp_path / "out", BATCH) == {
        "checked": True, "ok": True, "expected": hashlib.sha256(RAW_BYTES).hexdigest(),
        "file": "AAPL_message_1.csv"}


def test_manifest_check_fails_when_raw_object_changed_consistently(uploaded, tmp_path):
    key = ("bucket", f"raw/{BATCH}/AAPL_message_1.csv")
    forged = b"forged"
    uploaded.store[key] = (forged, {"sha256": hashlib.sha256(forged).hexdigest()})
    r2_lake.download_and_verify(uploaded, "bucket", BATCH, tmp_path / "out")
    assert r2_lake.check_against_manifest(tmp_path / "out", BATCH)["ok"] is False


def test_query_sql_points_at_the_batch_parquet():
    sql = r2_lake.build_query("summary", "my-bucket", BATCH)
    assert f"read_parquet('s3://my-bucket/curated/{BATCH}/validated_messages.parquet')" in sql


@pytest.mark.parametrize("name,bucket,batch", [
    ("drop-table", "bucket", BATCH),
    ("summary", "bucket", "x'); DROP TABLE t; --"),
    ("summary", "Bad Bucket!", BATCH),
])
def test_query_rejects_unsafe_input(name, bucket, batch):
    with pytest.raises(ValueError):
        r2_lake.build_query(name, bucket, batch)


def test_cli_without_credentials_exits_cleanly(monkeypatch, capsys):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.delenv(k, raising=False)
    assert r2_lake.main(["list"]) == 2
    assert "Set R2_ACCOUNT_ID" in capsys.readouterr().err
