"""
Pre-trip ETA forecast for train 169.

Wraps IBM's Tiny Time Mixer (TTM) `granite-timeseries-ttm-r2` for zero-shot
multivariate forecasting. The matrix shape is (days, 45 stations) of
arrival delays in minutes. We forecast the next H days and stitch
station-level confidence intervals from validation residuals.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MATRIX_PATH = DATA_DIR / "delay_matrix.parquet"
RESIDUALS_PATH = DATA_DIR / "ttm_residuals.npy"
STATION_ORDER_PATH = DATA_DIR / "station_order.csv"
METRICS_PATH = DATA_DIR / "ttm_metrics.json"

CTX = 512
HORIZON = 7
MODEL_ID = "ibm-granite/granite-timeseries-ttm-r2"


@dataclass
class PretripPrediction:
    target_date: pd.Timestamp
    station_name: str
    station_idx: int
    p50: float
    p05: float
    p95: float


@lru_cache(maxsize=1)
def _load_matrix() -> pd.DataFrame:
    return pd.read_parquet(MATRIX_PATH).ffill().bfill()


@lru_cache(maxsize=1)
def _load_station_order() -> pd.DataFrame:
    return pd.read_csv(STATION_ORDER_PATH)


@lru_cache(maxsize=1)
def _load_residuals() -> np.ndarray:
    return np.load(RESIDUALS_PATH)


@lru_cache(maxsize=1)
def load_metrics() -> Optional[dict]:
    if not METRICS_PATH.exists():
        return None
    import json

    return json.loads(METRICS_PATH.read_text())


@lru_cache(maxsize=1)
def _load_model():
    warnings.filterwarnings("ignore")
    from tsfm_public import TinyTimeMixerForPrediction

    model = TinyTimeMixerForPrediction.from_pretrained(
        MODEL_ID,
        num_input_channels=45,
        prediction_filter_length=HORIZON,
    )
    model.eval()
    return model


def stations() -> list[str]:
    return _load_station_order().sort_values("idx")["station_name"].tolist()


def forecast_next_days(days: int = HORIZON) -> np.ndarray:
    """Run TTM zero-shot. Returns array shape (days, 45) of predicted arr_delay."""
    import torch

    days = max(1, min(days, HORIZON))
    mat = _load_matrix()
    arr = mat.values.astype(np.float32)
    ctx = arr[-CTX:]

    mean = ctx.mean(axis=0, keepdims=True)
    std = ctx.std(axis=0, keepdims=True) + 1e-6
    ctx_norm = (ctx - mean) / std

    model = _load_model()
    x = torch.from_numpy(ctx_norm).unsqueeze(0)
    with torch.no_grad():
        out = model(past_values=x).prediction_outputs.numpy()[0]

    pred = out * std + mean
    return pred[:days]


def predict(target_date: pd.Timestamp, station_idx: int) -> PretripPrediction:
    """Return point + 90% CI for a given (date, station) using TTM forecast + residual percentiles."""
    mat = _load_matrix()
    last_date = mat.index.max()
    target_date = pd.Timestamp(target_date).normalize()

    days_ahead = (target_date - last_date).days
    if days_ahead < 1:
        raise ValueError(f"target_date must be after {last_date.date()}")
    if days_ahead > HORIZON:
        raise ValueError(f"target_date is more than {HORIZON} days ahead")

    forecast = forecast_next_days(days=days_ahead)
    point = float(forecast[days_ahead - 1, station_idx])

    res = _load_residuals()
    lower = point - float(np.percentile(res, 95))
    upper = point - float(np.percentile(res, 5))

    name = stations()[station_idx]
    return PretripPrediction(
        target_date=target_date,
        station_name=name,
        station_idx=station_idx,
        p50=point,
        p05=lower,
        p95=upper,
    )
