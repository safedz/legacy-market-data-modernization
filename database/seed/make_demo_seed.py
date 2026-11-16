"""Create a small, synthetic demo dataset (with a few deliberate bad rows) and run it through the
real pipeline into data/sim/. Lets the backend and frontend be developed and demoed without the
118k-row sample and with rejected records present.

    python database/seed/make_demo_seed.py
    psql -f database/seed/load_seed.sql        (from the project root)
    psql -f database/schema/schema.sql
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "quality-service" / "src",
          *(ROOT / s / "src" for s in ("ingestion-service", "transformation-service", "validation-service"))):
    sys.path.insert(0, str(p))

from fault_injection import inject_faults
from ingest import ingest_data
from lobster_sim import write_files
from transform import transform_data
from validate_data import validate_data


def main(n_messages=3000, per_fault=2):
    out = ROOT / "data" / "sim"
    msg, _ = write_files(out / "src", n_messages=n_messages)
    seeded = out / msg.name
    inject_faults(msg, seeded, per_fault=per_fault)
    data = out / "data"
    ingest_data(seeded, data)
    transform_data(data)
    report = validate_data(data)
    print("\nSeed ready:", report["stages"]["valid"]["records"], "valid,",
          report["stages"]["rejected"]["records"], "rejected")


if __name__ == "__main__":
    main()
