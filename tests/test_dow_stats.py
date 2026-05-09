import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import dow_stats


def _make_df(rows):
    return pd.DataFrame(rows, columns=["date", "arr_delay"])


class TestComputeDowStats:
    def test_empty_dataframe_returns_empty_table(self):
        result = dow_stats.compute_dow_stats(_make_df([]))
        assert list(result.index) == dow_stats.DOW_ORDER
        assert result["count"].isna().all() or (result["count"].fillna(0) == 0).all()

    def test_single_monday_observation(self):
        df = _make_df([("2026-05-04", 10)])  # 2026-05-04 is Monday
        s = dow_stats.compute_dow_stats(df, on_time_threshold=30)
        assert s.loc["Monday", "count"] == 1
        assert s.loc["Monday", "mean"] == 10
        assert s.loc["Monday", "on_time_pct"] == 100
        assert pd.isna(s.loc["Tuesday", "count"])

    def test_quantiles_sorted(self):
        rows = [("2026-05-04", v) for v in range(101)]  # all Mondays 0..100
        s = dow_stats.compute_dow_stats(df=_make_df(rows))
        assert s.loc["Monday", "p05"] < s.loc["Monday", "p50"] < s.loc["Monday", "p95"]
        assert s.loc["Monday", "median"] == 50

    def test_on_time_threshold_applies(self):
        rows = [("2026-05-04", 5), ("2026-05-04", 10), ("2026-05-04", 60)]
        s = dow_stats.compute_dow_stats(_make_df(rows), on_time_threshold=30)
        assert s.loc["Monday", "on_time_pct"] == pytest.approx(2 / 3 * 100)

    def test_full_week(self):
        # 2026-05-04 Mon → 2026-05-10 Sun
        rows = [
            ("2026-05-04", 5),   # Mon
            ("2026-05-05", 50),  # Tue
            ("2026-05-06", 0),   # Wed
            ("2026-05-07", 10),  # Thu
            ("2026-05-08", 100), # Fri
            ("2026-05-09", 20),  # Sat
            ("2026-05-10", 15),  # Sun
        ]
        s = dow_stats.compute_dow_stats(_make_df(rows))
        for dow in dow_stats.DOW_ORDER:
            assert s.loc[dow, "count"] == 1


class TestWorstAndBestDow:
    def test_worst_picks_highest_median(self):
        rows = [
            ("2026-05-04", 5),
            ("2026-05-05", 50),
            ("2026-05-06", 0),
        ]
        s = dow_stats.compute_dow_stats(_make_df(rows))
        assert dow_stats.worst_dow(s) == "Tuesday"

    def test_best_picks_lowest_median(self):
        rows = [
            ("2026-05-04", 5),
            ("2026-05-05", 50),
            ("2026-05-06", 0),
        ]
        s = dow_stats.compute_dow_stats(_make_df(rows))
        assert dow_stats.best_dow(s) == "Wednesday"

    def test_returns_none_when_all_nan(self):
        empty = dow_stats.compute_dow_stats(_make_df([]))
        assert dow_stats.worst_dow(empty) is None
        assert dow_stats.best_dow(empty) is None
