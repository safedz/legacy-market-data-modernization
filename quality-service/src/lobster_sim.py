
import random

import pandas as pd

RAW_COLUMNS = ["time", "event_type", "order_id", "size", "price", "direction"]
SENTINEL = 9_999_999_999
MID = 5_850_000
TICK = 100


def simulate(n_messages=2000, levels=5, seed=7):
    rng = random.Random(seed)
    orders = {}  
    asks, bids = {}, {}  
    rows, snapshots = [], []
    t, next_id = 34200.0, 1_000_000

    def book_side(side, reverse):
        out = []
        for price in sorted(side, reverse=reverse)[:levels]:
            out += [price, side[price]]
        while len(out) < levels * 2:
            out += [SENTINEL if not reverse else -SENTINEL, 0]
        return out

    def snapshot():
        a, b = book_side(asks, False), book_side(bids, True)
        snap = []
        for i in range(levels):
            snap += [a[2 * i], a[2 * i + 1], b[2 * i], b[2 * i + 1]]
        return snap

    def side_of(direction):
        return asks if direction == -1 else bids

    def add_level(direction, price, size):
        side = side_of(direction)
        side[price] = side.get(price, 0) + size

    def remove_level(direction, price, size):
        side = side_of(direction)
        side[price] -= size
        if side[price] <= 0:
            del side[price]

    for _ in range(n_messages):
        t += rng.expovariate(1 / 0.01)
        roll = rng.random()
        if not orders or roll < 0.42:
            direction = rng.choice((-1, 1))
            offset = rng.randint(1, 4) * TICK
            price = MID + offset if direction == -1 else MID - offset
            size = rng.randint(1, 300)
            next_id += 1
            orders[next_id] = [price, size, direction]
            add_level(direction, price, size)
            rows.append((t, 1, next_id, size, price, direction))
        elif roll < 0.67:
            oid = rng.choice(list(orders))
            price, size, direction = orders.pop(oid)
            remove_level(direction, price, size)
            rows.append((t, 3, oid, size, price, direction))
        elif roll < 0.80:
            oid = rng.choice(list(orders))
            price, size, direction = orders[oid]
            if size < 2:
                continue
            cut = rng.randint(1, size - 1)
            orders[oid][1] -= cut
            remove_level(direction, price, cut)
            rows.append((t, 2, oid, cut, price, direction))
        elif roll < 0.93:
            oid = rng.choice(list(orders))
            price, size, direction = orders[oid]
            fill = rng.randint(1, size)
            remove_level(direction, price, fill)
            if fill == size:
                del orders[oid]
            else:
                orders[oid][1] -= fill
            rows.append((t, 4, oid, fill, price, direction))
        else:
            direction = rng.choice((-1, 1))
            price = MID + direction * TICK
            rows.append((t, 5, rng.randint(1, 999), rng.randint(1, 50), price, direction))
        snapshots.append(snapshot())

    messages = pd.DataFrame(rows, columns=RAW_COLUMNS)
    book_cols = []
    for i in range(1, levels + 1):
        book_cols += [f"ask_price_{i}", f"ask_size_{i}", f"bid_price_{i}", f"bid_size_{i}"]
    return messages, pd.DataFrame(snapshots, columns=book_cols)


def write_files(directory, name="SIM_2012-06-21_34200000_57600000", **kwargs):
    from pathlib import Path

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    messages, book = simulate(**kwargs)
    msg_path = directory / f"{name}_message_1.csv"
    book_path = directory / f"{name}_orderbook_1.csv"
    messages.to_csv(msg_path, header=False, index=False, float_format="%.9f")
    book.to_csv(book_path, header=False, index=False)
    return msg_path, book_path


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "data/sim"
    print(write_files(target, n_messages=5000))
