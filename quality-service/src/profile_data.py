
import pandas as pd

LABELS = {1: "SUBMIT", 2: "CANCEL_PARTIAL", 3: "DELETE", 4: "EXECUTE_VISIBLE",
          5: "EXECUTE_HIDDEN", 6: "CROSS_TRADE", 7: "HALT"}


def _q(series, points=(0.5, 0.9, 0.99)):
    series = series.dropna()
    if series.empty:
        return {}
    out = {f"p{int(p * 100)}": float(series.quantile(p)) for p in points}
    out["min"], out["max"], out["mean"] = (
        float(series.min()), float(series.max()), float(series.mean()))
    return out


def profile(messages):
    df = messages.copy()
    for c in ("time", "event_type", "order_id", "size", "price", "direction"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n = len(df)
    if n == 0:
        return {"rows": 0}

    by_type = df["event_type"].value_counts().sort_index()
    event_mix = {
        LABELS.get(int(k), str(int(k))): {"count": int(v), "share": round(v / n, 6)}
        for k, v in by_type.items()
    }

    per_minute = df.groupby((df["time"] // 60).astype(int)).size()
    per_second = df.groupby(df["time"].astype(int)).size()
    busiest = per_second.sort_values(ascending=False).head(5)

    submits = df[df["event_type"] == 1]
    first_submit = submits.drop_duplicates("order_id").set_index("order_id")["time"]
    deletes = df[df["event_type"] == 3].drop_duplicates("order_id").set_index("order_id")["time"]
    lifetime_ms = ((deletes - first_submit.reindex(deletes.index)) * 1000).dropna()
    lifetime_ms = lifetime_ms[lifetime_ms >= 0]

    n_submit = int((df["event_type"] == 1).sum())
    n_cancel = int(df["event_type"].isin([2, 3]).sum())
    prices = df.loc[df["event_type"].isin([1, 2, 3, 4, 5]), "price"] / 10000

    return {
        "rows": int(n),
        "time_span_seconds": float(df["time"].max() - df["time"].min()),
        "event_mix": event_mix,
        "messages_per_minute": {
            "mean": float(per_minute.mean()),
            "peak": int(per_minute.max()),
            "quietest": int(per_minute.min()),
        },
        "busiest_seconds": {int(k): int(v) for k, v in busiest.items()},
        "submit_size": _q(submits["size"]),
        "price_dollars": _q(prices),
        "cancel_to_submit_ratio": round(n_cancel / n_submit, 4) if n_submit else None,
        "visible_execution_share": round(int((df["event_type"] == 4).sum()) / n, 6),
        "order_lifetime_ms_submit_to_delete": _q(lifetime_ms, (0.5, 0.9, 0.99)),
        "orders_deleted_within_1ms": int((lifetime_ms < 1).sum()),
        "orders_deleted_within_50ms": int((lifetime_ms < 50).sum()),
        "duplicates_flagged": int(df["is_duplicate"].astype(str).eq("True").sum())
        if "is_duplicate" in df.columns else None,
    }
