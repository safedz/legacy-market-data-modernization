"""Surveillance stage: rule-based alerts on the validated LOBSTER message stream.

SPOOFING and RAPID_CANCEL mirror surveillance/queries/spoofing.sql and
rapid_cancel.sql (and the rules in database/schema/schema.sql), so the Python
stage and the database should flag the same orders. BURST_ACTIVITY is a new rule.

Output: data/processed/surveillance_alerts.csv
"""
from pathlib import Path
import argparse

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"

SUBMIT, DELETE = 1, 3  


CONFIG = {
    "spoofing": {
        "size_percentile": 0.90,   
        "max_lifetime_s": 0.001,   
        "severity": "HIGH",
    },
    "rapid_cancel": {
        "min_lifetime_s": 0.001,   
        "max_lifetime_s": 0.05,    
        "severity": "MEDIUM",
    },
    "burst": {
        "window_s": 1,             
        "multiplier": 10,          
        "min_messages": 100,      
        "severity": "MEDIUM",
    },
}

SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
COLUMNS = ["alert_id", "alert_type", "order_id", "severity", "description",
           "alert_timestamp", "batch_id", "size", "lifetime_ms"]
NEEDED = ["time", "event_type", "order_id", "size", "price_dollars",
          "event_timestamp", "is_duplicate", "batch_id", "validation_status"]


def load_messages(path=None):
    path = Path(path) if path else PROCESSED / "validated_messages.csv"
    df = pd.read_csv(path, usecols=NEEDED)
    df["is_duplicate"] = df["is_duplicate"].astype(str).str.lower().eq("true")
    return df[df["validation_status"] == "VALID"].reset_index(drop=True)


def order_lifetimes(df):
    """One row per submitted order that was later deleted, with its lifetime."""
    live = df[~df["is_duplicate"]]
    subs = live[live["event_type"] == SUBMIT]
    dels = live[live["event_type"] == DELETE][["order_id", "batch_id", "time"]]
    m = subs.merge(dels, on=["order_id", "batch_id"], suffixes=("", "_del"))
    m["lifetime_s"] = m["time_del"] - m["time"]
    return m[m["lifetime_s"] >= 0].reset_index(drop=True)


def _empty():
    return pd.DataFrame(columns=COLUMNS[1:])


def _cancel_alerts(hit, alert_type, severity, text):
    if hit.empty:
        return _empty()
    ms = (hit["lifetime_s"] * 1000).round(3)
    return pd.DataFrame({
        "alert_type": alert_type,
        "order_id": hit["order_id"].astype(str),
        "severity": severity,
        "description": [text(s, m) for s, m in zip(hit["size"], ms)],
        "alert_timestamp": hit["event_timestamp"],
        "batch_id": hit["batch_id"],
        "size": hit["size"],
        "lifetime_ms": ms,
    })


def detect_spoofing(df, cfg=CONFIG["spoofing"]):
   
    threshold = df.loc[df["event_type"] == SUBMIT, "size"].quantile(cfg["size_percentile"])
    life = order_lifetimes(df)
    hit = life[(life["lifetime_s"] < cfg["max_lifetime_s"]) & (life["size"] > threshold)]
    pct = int(round((1 - cfg["size_percentile"]) * 100))
    return _cancel_alerts(
        hit, "SPOOFING", cfg["severity"],
        lambda s, m: f"Order of size {s} (top {pct}% by size) cancelled {m} ms after submission")


def detect_rapid_cancel(df, cfg=CONFIG["rapid_cancel"]):
    life = order_lifetimes(df)
    hit = life[(life["lifetime_s"] >= cfg["min_lifetime_s"]) &
               (life["lifetime_s"] < cfg["max_lifetime_s"])]
    return _cancel_alerts(
        hit, "RAPID_CANCEL", cfg["severity"],
        lambda s, m: f"Order of size {s} cancelled {m} ms after submission")


def detect_bursts(df, cfg=CONFIG["burst"]):
    live = df[~df["is_duplicate"]].copy()
    if live.empty:
        return _empty()
    live["window"] = (live["time"] // cfg["window_s"]).astype("int64")
    counts = (live.groupby(["batch_id", "window"])
                  .agg(messages=("time", "size"), first_ts=("event_timestamp", "min"))
                  .reset_index())
    median = counts.groupby("batch_id")["messages"].transform("median")
    threshold = (median * cfg["multiplier"]).clip(lower=cfg["min_messages"])
    mask = counts["messages"] >= threshold
    hit, med = counts[mask], median[mask]
    if hit.empty:
        return _empty()
    return pd.DataFrame({
        "alert_type": "BURST_ACTIVITY",
        "order_id": "N/A",
        "severity": cfg["severity"],
        "description": [f"{m} messages in a {cfg['window_s']} s window, {m / d:.0f}x the batch median"
                        for m, d in zip(hit["messages"], med)],
        "alert_timestamp": hit["first_ts"],
        "batch_id": hit["batch_id"],
        "size": hit["messages"],
        "lifetime_ms": float("nan"),
    })


def run_surveillance(input_file=None, output_file=None, config=None):
    cfg = config or CONFIG
    df = load_messages(input_file)
    parts = [detect_spoofing(df, cfg["spoofing"]),
             detect_rapid_cancel(df, cfg["rapid_cancel"]),
             detect_bursts(df, cfg["burst"])]
    parts = [p for p in parts if not p.empty]
    alerts = pd.concat(parts, ignore_index=True) if parts else _empty()

    if not alerts.empty:
        alerts["_rank"] = alerts["severity"].map(SEVERITY_RANK)
        alerts = (alerts.sort_values(["_rank", "alert_timestamp"])
                        .drop(columns="_rank").reset_index(drop=True))
    alerts.insert(0, "alert_id", range(1, len(alerts) + 1))

    out = Path(output_file) if output_file else PROCESSED / "surveillance_alerts.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    alerts[COLUMNS].to_csv(out, index=False)

    by_type = alerts["alert_type"].value_counts().to_dict()
    print("=== SURVEILLANCE ===")
    print(f"messages scanned : {len(df)}")
    print(f"alerts           : {len(alerts)}  {by_type}")
    print(f"written to       : {out}")
    return {"messages_scanned": len(df), "alerts_total": len(alerts),
            "by_type": by_type, "output_file": str(out)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run surveillance rules")
    ap.add_argument("--input", help="validated_messages.csv path")
    ap.add_argument("--output", help="alerts CSV path")
    a = ap.parse_args()
    run_surveillance(a.input, a.output)
