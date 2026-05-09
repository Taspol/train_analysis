"""Day-of-week aggregation helpers for train delay analysis."""

from __future__ import annotations

from typing import Optional

import pandas as pd

DOW_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def compute_dow_stats(df: pd.DataFrame, on_time_threshold: int = 30) -> pd.DataFrame:
    """Aggregate per-day-of-week delay statistics.

    df must have a datetime 'date' column and a numeric 'arr_delay' column.
    Returns a DataFrame indexed by DOW_ORDER with columns:
        count, mean, median, p05, p50, p95, on_time_pct.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["count", "mean", "median", "p05", "p50", "p95", "on_time_pct"],
            index=pd.Index(DOW_ORDER, name="day_of_week"),
        )

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work["dow"] = work["date"].dt.day_name()

    grouped = work.groupby("dow")["arr_delay"]
    stats = pd.DataFrame(
        {
            "count": grouped.size(),
            "mean": grouped.mean(),
            "median": grouped.median(),
            "p05": grouped.quantile(0.05),
            "p50": grouped.quantile(0.50),
            "p95": grouped.quantile(0.95),
            "on_time_pct": grouped.apply(
                lambda s: (s <= on_time_threshold).mean() * 100
            ),
        }
    )
    stats.index.name = "day_of_week"
    return stats.reindex(DOW_ORDER)


def worst_dow(stats: pd.DataFrame, metric: str = "median") -> Optional[str]:
    """Return the DOW with the highest value for the given metric."""
    valid = stats[metric].dropna()
    return None if valid.empty else valid.idxmax()


def best_dow(stats: pd.DataFrame, metric: str = "median") -> Optional[str]:
    valid = stats[metric].dropna()
    return None if valid.empty else valid.idxmin()
