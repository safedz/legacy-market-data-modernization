
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import platform

import pandas as pd


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_run_manifest(data_dir, extra_inputs=(), pipeline_version="unknown", gates=None):
    data_dir = Path(data_dir)
    outputs = []
    for sub in ("processed", "rejected", "lake/curated"):
        folder = data_dir / sub
        if folder.exists():
            outputs += sorted(p for p in folder.rglob("*")
                              if p.is_file() and p.name != "run_manifest.json"
                              and p.name != ".gitkeep")
    inputs = [Path(p) for p in extra_inputs if p and Path(p).exists()]

    def entry(p):
        return {"path": p.relative_to(data_dir).as_posix() if p.is_relative_to(data_dir)
                else p.as_posix(),
                "bytes": p.stat().st_size, "sha256": sha256_of(p)}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": pipeline_version,
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "inputs": [entry(p) for p in inputs],
        "outputs": [entry(p) for p in outputs],
        "gates": gates or {},
    }


def verify_run_manifest(data_dir, manifest):
    """Return the list of files whose hash no longer matches the manifest."""
    data_dir = Path(data_dir)
    bad = []
    for item in manifest["outputs"]:
        p = data_dir / item["path"]
        if not p.exists() or sha256_of(p) != item["sha256"]:
            bad.append(item["path"])
    return bad
