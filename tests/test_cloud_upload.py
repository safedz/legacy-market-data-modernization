import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "deployment" / "cloud", ROOT / "quality-service" / "src",
          *(ROOT / s / "src" for s in ("ingestion-service", "transformation-service", "validation-service"))):
    sys.path.insert(0, str(p))
sys.path.insert(0, str(ROOT))

import upload_to_r2 as r2


class FakeS3:
    def __init__(self, corrupt=False):
        self.store, self.corrupt = {}, corrupt

    def upload_file(self, path, bucket, key, ExtraArgs=None):
        data = Path(path).read_bytes()
        meta = dict((ExtraArgs or {}).get("Metadata", {}))
        if self.corrupt:
            meta["sha256"] = "0" * 64
        self.store[(bucket, key)] = (len(data), meta)

    def head_object(self, Bucket, Key):
        size, meta = self.store[(Bucket, Key)]
        return {"ContentLength": size, "Metadata": meta}


@pytest.fixture
def run_dir(tmp_path):
    from lobster_sim import write_files
    from ingest import ingest_data
    from transform import transform_data
    from validate_data import validate_data
    from run_quality import run_quality
    import shutil
    msg, book = write_files(tmp_path / "src", n_messages=500)
    data = tmp_path / "data"
    (data / "raw").mkdir(parents=True)
    shutil.copy(book, data / "raw" / book.name)
    ingest_data(msg, data); transform_data(data); validate_data(data); run_quality(data)
    return data


def test_plan_covers_raw_curated_and_reports(run_dir):
    keys = [k for _, k in r2.plan_uploads(run_dir)]
    assert any(k.startswith("raw/") and k.endswith("_message_1.csv") for k in keys)
    assert any(k.startswith("curated/") for k in keys)
    assert sum(k.startswith("reports/") for k in keys) >= 4


def test_upload_verifies_every_object(run_dir):
    results = r2.upload_batch(FakeS3(), "bucket", r2.plan_uploads(run_dir))
    assert results and all(r["verified"] for r in results)
    raw = next(r for r in results if r["key"].startswith("raw/"))
    src = next(p for p, k in r2.plan_uploads(run_dir) if k.startswith("raw/"))
    assert raw["sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()


def test_corrupted_upload_is_flagged(run_dir):
    results = r2.upload_batch(FakeS3(corrupt=True), "bucket", r2.plan_uploads(run_dir))
    assert not any(r["verified"] for r in results)


def test_no_credentials_means_safe_dry_run(run_dir, monkeypatch, capsys):
    for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.delenv(k, raising=False)
    assert r2.main(["--data-dir", str(run_dir)]) == 0
    assert "DRY RUN" in capsys.readouterr().out


def test_missing_pipeline_output_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        r2.plan_uploads(tmp_path)
