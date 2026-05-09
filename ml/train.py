"""
Reproducible training pipeline. Run once after dataset refresh:

    python3 -m ml.train

Outputs go to ./data/:
    - delay_matrix.parquet       pivoted (date × station_idx) delay matrix
    - station_order.csv          canonical station ordering
    - ttm_residuals.npy          walk-forward residuals for TTM 90% CI
    - live_eta_model.pkl         joblib bundle of q05/q50/q95 regressors
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC_CSV = ROOT / "station_delays.csv"
DATA_DIR = ROOT / "data"

MATRIX_PATH = DATA_DIR / "delay_matrix.parquet"
STATION_ORDER_PATH = DATA_DIR / "station_order.csv"
RESIDUALS_PATH = DATA_DIR / "ttm_residuals.npy"
LIVE_MODEL_PATH = DATA_DIR / "live_eta_model.pkl"

CTX = 512
HORIZON = 7
TTM_VAL_DAYS = 60
TTM_MODEL_ID = "ibm-granite/granite-timeseries-ttm-r2"


def build_matrix() -> pd.DataFrame:
    df = pd.read_csv(SRC_CSV)
    df["arr_delay"] = pd.to_numeric(df["arr_delay"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])

    first_day = df["date"].min()
    canon = (
        df[df["date"] == first_day][["station_name"]]
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "idx"})
    )
    canon[["idx", "station_name"]].to_csv(STATION_ORDER_PATH, index=False)

    order_map = canon.set_index("station_name")["idx"].to_dict()
    df["stn_idx"] = df["station_name"].map(order_map)
    df = df.dropna(subset=["stn_idx"])
    df["stn_idx"] = df["stn_idx"].astype(int)

    mat = df.pivot_table(index="date", columns="stn_idx", values="arr_delay", aggfunc="mean")
    mat = mat.sort_index().reindex(columns=range(45))
    full_idx = pd.date_range(mat.index.min(), mat.index.max(), freq="D")
    mat = mat.reindex(full_idx).ffill().bfill()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    mat.to_parquet(MATRIX_PATH)
    return mat


def compute_ttm_residuals(mat: pd.DataFrame) -> np.ndarray:
    warnings.filterwarnings("ignore")
    import torch
    from tsfm_public import TinyTimeMixerForPrediction

    arr = mat.values.astype(np.float32)
    model = TinyTimeMixerForPrediction.from_pretrained(
        TTM_MODEL_ID,
        num_input_channels=45,
        prediction_filter_length=HORIZON,
    )
    model.eval()

    preds, trues = [], []
    for end in range(len(arr) - TTM_VAL_DAYS, len(arr) - HORIZON + 1):
        ctx = arr[end - CTX : end]
        target = arr[end : end + HORIZON]
        mean = ctx.mean(axis=0, keepdims=True)
        std = ctx.std(axis=0, keepdims=True) + 1e-6
        ctx_norm = (ctx - mean) / std

        x = torch.from_numpy(ctx_norm).unsqueeze(0)
        with torch.no_grad():
            out = model(past_values=x).prediction_outputs.numpy()[0]
        preds.append(out * std + mean)
        trues.append(target)

    residuals = (np.stack(preds) - np.stack(trues)).reshape(-1)
    np.save(RESIDUALS_PATH, residuals)
    return residuals


def train_live_eta(mat: pd.DataFrame) -> dict:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import train_test_split

    n_stations = mat.shape[1]
    records = []
    for date_str, row in mat.iterrows():
        delays = row.values
        dow = pd.Timestamp(date_str).dayofweek
        month = pd.Timestamp(date_str).month
        for cur in range(n_stations - 1):
            cur_delay = delays[cur]
            for tgt in range(cur + 1, n_stations):
                records.append((cur, cur_delay, tgt, tgt - cur, dow, month, delays[tgt]))

    cols = ["cur_idx", "cur_delay", "tgt_idx", "gap", "dow", "month", "tgt_delay"]
    train_df = pd.DataFrame(records, columns=cols)
    X = train_df[cols[:-1]].values
    y = train_df["tgt_delay"].values
    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.15, random_state=42)

    bundle = {"feature_names": cols[:-1]}
    for q, name in [(0.05, "q05"), (0.5, "q50"), (0.95, "q95")]:
        m = GradientBoostingRegressor(
            loss="quantile",
            alpha=q,
            n_estimators=200,
            max_depth=4,
            random_state=42,
        )
        m.fit(X_train, y_train)
        bundle[name] = m

    joblib.dump(bundle, LIVE_MODEL_PATH)
    return bundle


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("step 1/3: build matrix")
    mat = build_matrix()
    print(f"  matrix shape: {mat.shape}")

    print("step 2/3: TTM walk-forward residuals")
    res = compute_ttm_residuals(mat)
    print(f"  residual count: {len(res)}, p5/p95: {np.percentile(res, 5):.1f} / {np.percentile(res, 95):.1f}")

    print("step 3/3: live ETA quantile model")
    train_live_eta(mat)
    print(f"  saved → {LIVE_MODEL_PATH}")


if __name__ == "__main__":
    main()
