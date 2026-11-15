
validation-service tests
`test_validation_rules.py` exercises each rejection rule one at a time (price, direction, event type,
time bounds, size, non-numeric, halt fields), multiple reasons on one record, duplicates being flagged
but kept, and a batch where every record is rejected. The end-to-end reject path on a full file is in
`quality-service/tests/test_reject_path.py` (fault injection).