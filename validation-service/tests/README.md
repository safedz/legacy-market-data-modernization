
# Validation Service Tests

`test_validation_rules.py` tests each data rejection rule individually, including:

- Price validation
- Direction validation
- Event type validation
- Time bounds
- Order size validation
- Non-numeric values
- Halt field validation

It also tests:

- Multiple rejection reasons for a single record
- Duplicate records being flagged but retained
- Batches where every record is rejected

## End-to-End Rejection Testing

The full-file rejection path is tested in:

`quality-service/tests/test_reject_path.py`

This test uses fault injection to verify that invalid records are correctly rejected throughout the pipeline.

## Run Tests

Run the validation service tests:

```bash
python -m pytest validation-service/tests -v
```

Run the end-to-end rejection test:

```bash
python -m pytest quality-service/tests/test_reject_path.py -v
```
