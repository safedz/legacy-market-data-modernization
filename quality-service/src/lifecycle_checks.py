
import pandas as pd

HARD_RULES = (
    "time_regressions",
    "event_before_submit",
    "price_changed_after_submit",
    "direction_changed_after_submit",
    "over_consumed_orders",
    "events_after_delete",
    "duplicate_submits",
)


def lifecycle_checks(messages):
    df = messages[
        ["source_record_number", "time", "event_type", "order_id", "size", "price", "direction"]
    ].apply(pd.to_numeric, errors="coerce")
    df = df.sort_values("source_record_number")

    order_events = df[df["event_type"].isin([1, 2, 3, 4])]
    submits = order_events[order_events["event_type"] == 1]
    others = order_events[order_events["event_type"] != 1]

    first_submit = submits.drop_duplicates("order_id", keep="first").set_index("order_id")
    linked = others.join(first_submit, on="order_id", rsuffix="_submit", how="inner")

    consumed = (
        linked[linked["event_type"].isin([2, 4])].groupby("order_id")["size"].sum()
    )
    submitted_size = first_submit["size"]
    over = (consumed > submitted_size.reindex(consumed.index)).sum()

    delete_record = (
        others[others["event_type"] == 3].groupby("order_id")["source_record_number"].min()
    )
    after = others.join(delete_record.rename("delete_record"), on="order_id", how="inner")
    after = after[after["source_record_number"] > after["delete_record"]]

    counts = {
        "time_regressions": int((df["time"].diff() < 0).sum()),
        "event_before_submit": int((linked["time"] < linked["time_submit"]).sum()),
        "price_changed_after_submit": int((linked["price"] != linked["price_submit"]).sum()),
        "direction_changed_after_submit": int(
            (linked["direction"] != linked["direction_submit"]).sum()
        ),
        "over_consumed_orders": int(over),
        "events_after_delete": int(len(after)),
        "duplicate_submits": int(submits["order_id"].duplicated().sum()),
    }
    orphan = int((~others["order_id"].isin(first_submit.index)).sum())

    return {
        "events_examined": int(len(order_events)),
        "orders_submitted": int(len(first_submit)),
        "violations": counts,
        "orphan_events": orphan,
        "orphan_share": round(orphan / len(others), 6) if len(others) else 0.0,
        "pass": all(v == 0 for v in counts.values()),
    }
