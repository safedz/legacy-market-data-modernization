import pandas as pd
import pytest

from orderbook_reconcile import book_sanity, load_orderbook, reconcile


def test_clean_data_reconciles_perfectly(sim_frames):
    messages, book = sim_frames
    r = reconcile(messages, book, min_match_rate=1.0)
    assert r["pass"] is True
    assert r["mismatched"] == 0
    assert r["matched"] == r["checked"] > 0
    assert r["coverage"] > 0.8
    assert r["hidden_execution_changed_book"] == 0


def test_tampered_size_is_detected(sim_frames):
    messages, book = sim_frames
    idx = messages.index[messages.event_type.isin([1, 3])][100:105]
    messages.loc[idx, "size"] += 7
    r = reconcile(messages, book, min_match_rate=1.0)
    assert r["mismatched"] == 5
    assert r["pass"] is False
    assert r["mismatch_samples"][0]["actual_change"] != r["mismatch_samples"][0]["expected_change"]


def test_wrong_price_is_detected(sim_frames):
    messages, book = sim_frames
    idx = messages.index[messages.event_type == 1][50]
    messages.loc[idx, "price"] += 100
    r = reconcile(messages, book, min_match_rate=1.0)
    assert r["mismatched"] >= 1


def test_hidden_execution_must_not_change_book(sim_frames):
    messages, book = sim_frames
    row = messages.index[messages.event_type == 5][10]
    book.loc[row, "ask_size_1"] += 1  
    r = reconcile(messages, book, min_match_rate=0.0)
    assert r["hidden_execution_changed_book"] >= 1
    assert r["pass"] is False


def test_levels_inferred_and_sanity_clean(sim_files):
    _, book_path = sim_files
    book = load_orderbook(book_path)
    assert book.shape[1] == 20
    s = book_sanity(book)
    assert s["levels"] == 5
    assert s["crossed_book_rows"] == 0
    assert s["ask_levels_not_ascending_rows"] == 0
    assert s["bid_levels_not_descending_rows"] == 0


def test_crossed_book_detected(sim_frames):
    _, book = sim_frames
    book.loc[10, "bid_price_1"] = book.loc[10, "ask_price_1"] + 100
    assert book_sanity(book)["crossed_book_rows"] == 1


def test_bad_column_count_rejected(tmp_path):
    p = tmp_path / "ob.csv"
    p.write_text("1,2,3\n4,5,6\n")
    with pytest.raises(ValueError):
        load_orderbook(p)


def test_one_level_file_like_the_real_sample(tmp_path):
    p = tmp_path / "ob.csv"
    p.write_text("5859400,200,5853300,18\n5859100,18,5853300,18\n5859100,18,5853300,36\n")
    book = load_orderbook(p)
    msgs = pd.DataFrame({"source_record_number": [2, 3], "event_type": [1, 1],
                         "size": [18, 18], "price": [5859100, 5853300],
                         "direction": [-1, 1]})
    r = reconcile(msgs, book, min_match_rate=1.0)
    
    assert r["mismatched"] == 0
    assert r["matched"] >= 1
