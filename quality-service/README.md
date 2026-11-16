
# Quality Service

Deeper checks that run after `validate_data.py`.

The validator proves that no record was lost. This service verifies that the records are correct using a second independent source.

## Modules

| Module | What It Does |
|---|---|
| `orderbook_reconcile.py` | Replays each message against the LOBSTER orderbook file. A SUBMIT of 50 shares at a price must raise the size at that price by exactly 50 between snapshots n-1 and n. DELETE, PARTIAL CANCEL, and EXECUTE must lower it, while HIDDEN execution must change nothing. Also checks snapshots for crossed books and level ordering. Messages outside the visible depth are counted as skipped, never as passed. |
| `lifecycle_checks.py` | Checks per-order rules: no event before submission, price and side never change, executions never exceed submitted size, nothing happens after deletion, no duplicate submissions, and timestamps never go backwards. Orphan events (orders submitted before the file starts) are reported but are normal for LOBSTER samples. |
| `profile_data.py` | Generates a data profile covering event mix, messages per minute, busiest seconds, size and price spread, order lifetimes, and the share of orders deleted within 1 ms / 50 ms. |
| `run_manifest.py` | Calculates SHA-256 hashes of every input and output of a run, along with Python and pandas versions. `verify_run_manifest` detects files changed afterwards. |
| `fault_injection.py` | Corrupts a copy of a message file using six kinds of faults, runs the actual pipeline, and checks that every fault is rejected for the correct reason and nothing else is rejected. |
| `lobster_sim.py` | Generates a synthetic LOBSTER message and orderbook pair with a perfectly consistent book, allowing reconciliation to be tested against known-correct data. |
| `run_quality.py` | Runs the checks and generates `quality_report.json`, `profile_report.json`, and `run_manifest.json` in `data/processed/`. |

## Run

Run all four pipeline stages:

```bash
python run_pipeline.py
```

Run only the original three stages:

```bash
python run_pipeline.py --skip-quality
```

Enable strict lifecycle validation:

```bash
python run_pipeline.py --strict
```

Set the minimum reconciliation match rate:

```bash
python run_pipeline.py --min-match-rate 0.95
```

Run fault injection:

```bash
python quality-service/src/fault_injection.py --input data/raw/AAPL_2012-06-21_34200000_57600000_message_1.csv
```

## Quality Gates

- **Reconciliation FAIL:** Stops the pipeline and returns exit code `1`.
- **Missing orderbook file:** Marked as `SKIPPED`, not a failure.
- **Lifecycle violations:** Reported as `WARN` by default, unless `--strict` is enabled.

## Tests

Run the quality service and validation service tests:

```bash
python -m pytest quality-service/tests validation-service/tests -v
```
