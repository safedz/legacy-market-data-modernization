import pandas as pd

from lifecycle_checks import lifecycle_checks
from profile_data import profile


def frame(rows):
    return pd.DataFrame(rows, columns=["source_record_number", "time", "event_type",
                                        "order_id", "size", "price", "direction"])


def test_clean_lifecycle_passes():
    df = frame([(1, 1.0, 1, 10, 100, 500, 1), (2, 2.0, 2, 10, 40, 500, 1),
                (3, 3.0, 4, 10, 30, 500, 1), (4, 4.0, 3, 10, 30, 500, 1)])
    r = lifecycle_checks(df)
    assert r["pass"] is True and r["orphan_events"] == 0


def test_orphans_are_informational_not_failures():
    df = frame([(1, 1.0, 3, 99, 10, 500, 1)])
    r = lifecycle_checks(df)
    assert r["orphan_events"] == 1 and r["pass"] is True


def test_each_hard_violation_detected():
    df = frame([
        (1, 5.0, 1, 10, 100, 500, 1),
        (2, 4.0, 2, 10, 20, 500, 1),     # time regression + before submit
        (3, 6.0, 4, 10, 20, 501, 1),     # price changed
        (4, 7.0, 4, 10, 20, 500, -1),    # direction changed
        (5, 8.0, 4, 10, 200, 500, 1),    # over-consumed
        (6, 9.0, 3, 10, 5, 500, 1),
        (7, 10.0, 2, 10, 1, 500, 1),     # after delete
        (8, 11.0, 1, 10, 50, 500, 1),    # duplicate submit
    ])
    v = lifecycle_checks(df)["violations"]
    for rule in ("time_regressions", "event_before_submit", "price_changed_after_submit",
                 "direction_changed_after_submit", "over_consumed_orders",
                 "events_after_delete", "duplicate_submits"):
        assert v[rule] >= 1, rule


def test_profile_basics():
    df = frame([(1, 60.0, 1, 1, 100, 1000000, 1), (2, 60.0005, 3, 1, 100, 1000000, 1),
                (3, 130.0, 1, 2, 50, 1010000, -1)])
    df["is_duplicate"] = False
    p = profile(df)
    assert p["rows"] == 3
    assert p["event_mix"]["SUBMIT"]["count"] == 2
    assert p["orders_deleted_within_1ms"] == 1
    assert p["cancel_to_submit_ratio"] == 0.5
    assert p["price_dollars"]["max"] == 101.0


def test_profile_empty():
    assert profile(frame([]))["rows"] == 0
