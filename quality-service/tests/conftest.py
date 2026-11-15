from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "quality-service" / "src", *(ROOT / s / "src" for s in
          ("ingestion-service", "transformation-service", "validation-service"))):
    sys.path.insert(0, str(p))

from lobster_sim import write_files, simulate  


@pytest.fixture
def sim_files(tmp_path):
    return write_files(tmp_path / "src", n_messages=3000)


@pytest.fixture
def sim_frames():
    messages, book = simulate(3000)
    messages.insert(0, "source_record_number", range(1, len(messages) + 1))
    return messages, book


@pytest.fixture
def pipeline_run(tmp_path, sim_files):
    from ingest import ingest_data
    from transform import transform_data
    from validate_data import validate_data

    msg, book = sim_files
    data_dir = tmp_path / "data"
    (data_dir / "raw").mkdir(parents=True)
    shutil.copy(book, data_dir / "raw" / book.name)
    ingest_data(msg, data_dir)
    transform_data(data_dir)
    validate_data(data_dir)
    return data_dir
