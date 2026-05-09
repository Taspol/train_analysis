"""
Live ETA refinement model for train 169.

Quantile gradient-boosted regression. Given the train's currently-observed
station + delay, predicts the delay at any subsequent station with a 90%
confidence band.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA_DIR / "live_eta_model.pkl"

FEATURE_NAMES = ["cur_idx", "cur_delay", "tgt_idx", "gap", "dow", "month"]


@dataclass
class LivePrediction:
    target_idx: int
    p50: float
    p05: float
    p95: float


@lru_cache(maxsize=1)
def _load_model() -> dict:
    return joblib.load(MODEL_PATH)


def predict(
    cur_idx: int,
    cur_delay: float,
    tgt_idx: int,
    today: date,
) -> LivePrediction:
    if tgt_idx <= cur_idx:
        raise ValueError("tgt_idx must be greater than cur_idx")
    bundle = _load_model()
    feats = np.array(
        [[cur_idx, cur_delay, tgt_idx, tgt_idx - cur_idx, today.weekday(), today.month]],
        dtype=float,
    )
    p05 = float(bundle["q05"].predict(feats)[0])
    p50 = float(bundle["q50"].predict(feats)[0])
    p95 = float(bundle["q95"].predict(feats)[0])
    if p05 > p95:
        p05, p95 = p95, p05
    return LivePrediction(target_idx=tgt_idx, p50=p50, p05=p05, p95=p95)


def predict_remaining(
    cur_idx: int,
    cur_delay: float,
    n_stations: int,
    today: date,
) -> list[LivePrediction]:
    return [
        predict(cur_idx, cur_delay, tgt, today)
        for tgt in range(cur_idx + 1, n_stations)
    ]
