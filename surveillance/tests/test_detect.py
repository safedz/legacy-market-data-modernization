import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detect import (detect_bursts, detect_rapid_cancel, detect_spoofing,  # noqa: E402
                    load_messages, run_surveillance)


def row(order_id, t, event, size=10, batch="b1", dup=False):
    return {"time": t, "event_type": event, "order_id": order_id, "size": size,
            "price_dollars": 100.0, "event_timestamp": f"2012-06-21 {t:013.6f}",
            "is_duplicate": dup, "batch_id": batch, "validation_status": "VALID"}


def order_flow():
    """20 normal orders (size 10, live 5 s) plus injected cases."""
    rows = []
    for i in range(20):
        rows += [row(1000 + i, 100 + i, 1), row(1000 + i, 105 + i, 3)]
    
    rows += [row(1, 200.0, 1, size=1000), row(1, 200.0005, 3, size=1000)]  
    rows += [row(2, 210.0, 1, size=1), row(2, 210.0005, 3, size=1)]        
    rows += [row(3, 220.0, 1, size=10), row(3, 220.010, 3, size=10)]       
    
    rows += [row(1000, 100.0002, 3, dup=True)]
    return pd.DataFrame(rows)


def test_spoofing_flags_only_large_fast_cancel():
    alerts = detect_spoofing(order_flow())
    assert list(alerts["order_id"]) == ["1"]
    assert alerts.iloc[0]["severity"] == "HIGH"


def test_rapid_cancel_flags_only_1_to_50_ms():
    alerts = detect_rapid_cancel(order_flow())
    assert list(alerts["order_id"]) == ["3"]
    assert alerts.iloc[0]["severity"] == "MEDIUM"


def test_rules_do_not_overlap():
    df = order_flow()
    spoof = set(detect_spoofing(df)["order_id"])
    rapid = set(detect_rapid_cancel(df)["order_id"])
    assert spoof.isdisjoint(rapid)


def test_burst_detected_once():
    rows, n = [], 0
    for s in range(20):                      
        for k in range(5):
            rows.append(row(n, 34200 + s + k / 10, 1))
            n += 1
    for k in range(500):                     
        rows.append(row(n, 34250 + k / 1000, 1))
        n += 1
    alerts = detect_bursts(pd.DataFrame(rows))
    assert len(alerts) == 1
    assert alerts.iloc[0]["alert_type"] == "BURST_ACTIVITY"


def test_quiet_market_has_no_burst():
    rows = [row(i, 34200 + i, 1) for i in range(50)]
    assert detect_bursts(pd.DataFrame(rows)).empty


def test_end_to_end_csv(tmp_path):
    src = tmp_path / "validated_messages.csv"
    out = tmp_path / "surveillance_alerts.csv"
    order_flow().to_csv(src, index=False)
    summary = run_surveillance(src, out)
    result = pd.read_csv(out)
    assert summary["alerts_total"] == 2
    assert list(result["alert_id"]) == [1, 2]
    assert list(result["alert_type"]) == ["SPOOFING", "RAPID_CANCEL"]  # HIGH before MEDIUM


def test_no_alerts_still_writes_header(tmp_path):
    src = tmp_path / "v.csv"
    out = tmp_path / "a.csv"
    pd.DataFrame([row(i, 34200 + i, 1) for i in range(5)]).to_csv(src, index=False)
    assert run_surveillance(src, out)["alerts_total"] == 0
    assert "alert_type" in out.read_text()


def test_invalid_rows_are_ignored(tmp_path):
    df = order_flow()
    df.loc[df["order_id"] == 1, "validation_status"] = "INVALID"
    src = tmp_path / "v.csv"
    df.to_csv(src, index=False)
    assert "1" not in set(detect_spoofing(load_messages(src))["order_id"])