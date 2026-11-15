
from pathlib import Path

import numpy as np
import pandas as pd

EMPTY_PRICE_LIMIT = 9_999_999_999  
BOOK_CHANGING = {1: 1, 2: -1, 3: -1, 4: -1}  
ASK_DIRECTION = -1 
MAX_MISMATCH_SAMPLES = 25


def load_orderbook(path):
    """Read a LOBSTER orderbook CSV. Levels are inferred from the column count."""
    book = pd.read_csv(path, header=None)
    if book.shape[1] % 4 != 0:
        raise ValueError(
            f"Orderbook file must have 4 columns per level, got {book.shape[1]}"
        )
    levels = book.shape[1] // 4
    names = []
    for i in range(1, levels + 1):
        names += [f"ask_price_{i}", f"ask_size_{i}", f"bid_price_{i}", f"bid_size_{i}"]
    book.columns = names
    return book


def _side_arrays(book, side):
    levels = book.shape[1] // 4
    prices = np.column_stack([book[f"{side}_price_{i}"] for i in range(1, levels + 1)])
    sizes = np.column_stack([book[f"{side}_size_{i}"] for i in range(1, levels + 1)])
    return prices.astype("float64"), sizes.astype("float64")


def _visible(prices, price, side):
    """True where `price` lies inside the depth shown by each snapshot row."""
    empty = np.abs(prices) >= EMPTY_PRICE_LIMIT
    has_empty = empty.any(axis=1) 
    if side == "ask":
        edge = np.where(empty, -np.inf, prices).max(axis=1)
        return has_empty | (price <= edge)
    edge = np.where(empty, np.inf, prices).min(axis=1)
    return has_empty | (price >= edge)


def _size_at(prices, sizes, price):
    return (sizes * (prices == price[:, None])).sum(axis=1)


def book_sanity(book):
    """Structural checks on the snapshot file itself."""
    ask_p, ask_s = _side_arrays(book, "ask")
    bid_p, bid_s = _side_arrays(book, "bid")
    ask_real = np.abs(ask_p) < EMPTY_PRICE_LIMIT
    bid_real = np.abs(bid_p) < EMPTY_PRICE_LIMIT

    best_ask = np.where(ask_real[:, 0], ask_p[:, 0], np.nan)
    best_bid = np.where(bid_real[:, 0], bid_p[:, 0], np.nan)
    crossed = int(np.nansum(best_bid >= best_ask))

    def unordered(prices, real, ascending):
        if prices.shape[1] < 2:
            return 0
        a, b = prices[:, :-1], prices[:, 1:]
        both = real[:, :-1] & real[:, 1:]
        bad = (b <= a) if ascending else (b >= a)
        return int((bad & both).any(axis=1).sum())

    return {
        "snapshot_rows": int(len(book)),
        "levels": int(book.shape[1] // 4),
        "crossed_book_rows": crossed,
        "ask_levels_not_ascending_rows": unordered(ask_p, ask_real, True),
        "bid_levels_not_descending_rows": unordered(bid_p, bid_real, False),
        "negative_size_rows": int(((ask_s < 0) | (bid_s < 0)).any(axis=1).sum()),
    }


def reconcile(messages, book, min_match_rate=0.99):
    """Compare messages with the orderbook snapshots.

    `messages` needs: source_record_number, event_type, size, price, direction
    (record number n pairs with snapshot row n-1, zero based).
    """
    msg = messages[["source_record_number", "event_type", "size", "price", "direction"]]
    msg = msg.apply(pd.to_numeric, errors="coerce").dropna()
    rec = msg["source_record_number"].astype(int).to_numpy()
    in_range = (rec >= 2) & (rec <= len(book))  
    msg, rec = msg[in_range], rec[in_range]

    result = {
        "orderbook_rows": int(len(book)),
        "messages_considered": int(len(msg)),
        "checked": 0,
        "matched": 0,
        "mismatched": 0,
        "skipped_outside_visible_depth": 0,
        "hidden_execution_checked": 0,
        "hidden_execution_changed_book": 0,
        "mismatch_samples": [],
    }

    snapshot_cols = {s: _side_arrays(book, s) for s in ("ask", "bid")}
    samples = []

    for direction, side in ((ASK_DIRECTION, "ask"), (1, "bid")):
        prices, sizes = snapshot_cols[side]
        for etype, sign in BOOK_CHANGING.items():
            sel = ((msg["event_type"] == etype) & (msg["direction"] == direction)).to_numpy()
            if not sel.any():
                continue
            r = rec[sel] - 1  
            price = msg.loc[sel, "price"].to_numpy(dtype="float64")
            delta = sign * msg.loc[sel, "size"].to_numpy(dtype="float64")

            prev_vis = _visible(prices[r - 1], price, side)
            cur_vis = _visible(prices[r], price, side)
            usable = prev_vis & cur_vis
            before = _size_at(prices[r - 1], sizes[r - 1], price)
            after = _size_at(prices[r], sizes[r], price)
            ok = (after - before) == delta

            result["checked"] += int(usable.sum())
            result["matched"] += int((usable & ok).sum())
            result["mismatched"] += int((usable & ~ok).sum())
            result["skipped_outside_visible_depth"] += int((~usable).sum())

            bad = np.flatnonzero(usable & ~ok)
            for k in bad[: MAX_MISMATCH_SAMPLES]:
                samples.append(
                    {
                        "source_record_number": int(r[k] + 1),
                        "event_type": etype,
                        "side": side,
                        "price": float(price[k]),
                        "expected_change": float(delta[k]),
                        "actual_change": float(after[k] - before[k]),
                    }
                )

    hidden = (msg["event_type"] == 5).to_numpy()
    if hidden.any():
        r = rec[hidden] - 1
        both = book.to_numpy(dtype="float64")
        changed = (both[r] != both[r - 1]).any(axis=1)
        result["hidden_execution_checked"] = int(hidden.sum())
        result["hidden_execution_changed_book"] = int(changed.sum())

    samples.sort(key=lambda s: s["source_record_number"])
    result["mismatch_samples"] = samples[:MAX_MISMATCH_SAMPLES]
    result["match_rate"] = (
        result["matched"] / result["checked"] if result["checked"] else None
    )
    result["coverage"] = (
        result["checked"] / result["messages_considered"]
        if result["messages_considered"]
        else None
    )
    result["min_match_rate"] = min_match_rate
    result["pass"] = bool(
        result["checked"] > 0
        and result["match_rate"] >= min_match_rate
        and result["hidden_execution_changed_book"] == 0
    )
    return result


def reconcile_files(messages_csv, orderbook_csv, min_match_rate=0.99):
    messages = pd.read_csv(messages_csv)
    book = load_orderbook(orderbook_csv)
    out = reconcile(messages, book, min_match_rate)
    out["book_sanity"] = book_sanity(book)
    out["orderbook_file"] = Path(orderbook_csv).name
    return out
