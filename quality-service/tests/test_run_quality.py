import json

import pytest

from run_manifest import verify_run_manifest
from run_quality import run_quality


def test_quality_stage_end_to_end(pipeline_run):
    q = run_quality(pipeline_run, min_match_rate=1.0)
    assert q["overall_pass"] is True
    assert q["gates"]["orderbook_reconciliation"] == "PASS"
    processed = pipeline_run / "processed"
    for name in ("quality_report.json", "profile_report.json", "run_manifest.json"):
        assert (processed / name).exists()


def test_run_manifest_hashes_verify_and_detect_tampering(pipeline_run):
    run_quality(pipeline_run)
    manifest = json.loads((pipeline_run / "processed" / "run_manifest.json").read_text())
    assert manifest["inputs"] and manifest["outputs"]
    assert verify_run_manifest(pipeline_run, manifest) == []
    victim = pipeline_run / "processed" / "validated_messages.csv"
    victim.write_text(victim.read_text() + "tampered\n")
    assert "processed/validated_messages.csv" in verify_run_manifest(pipeline_run, manifest)


def test_missing_orderbook_is_skipped_not_failed(pipeline_run):
    for f in (pipeline_run / "raw").glob("*orderbook*"):
        f.unlink()
    q = run_quality(pipeline_run)
    assert q["orderbook_reconciliation"]["status"] == "SKIPPED"
    assert q["overall_pass"] is True


def test_corrupted_messages_fail_the_gate(pipeline_run):
    import pandas as pd
    f = pipeline_run / "processed" / "validated_messages.csv"
    df = pd.read_csv(f)
    idx = df.index[df.event_type.isin([1, 3])][200:260]
    df.loc[idx, "size"] += 5
    df.to_csv(f, index=False)
    q = run_quality(pipeline_run, min_match_rate=0.999)
    assert q["orderbook_reconciliation"]["status"] == "FAIL"
    assert q["overall_pass"] is False


def test_run_quality_requires_pipeline_output(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_quality(tmp_path)
