import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml import pretrip


@pytest.fixture(autouse=True)
def _require_artifacts():
    missing = [p for p in (pretrip.MATRIX_PATH, pretrip.STATION_ORDER_PATH) if not p.exists()]
    if missing:
        pytest.skip(f"Missing data files: {missing}. Run `python3 -m ml.train` first.")


def test_stations_returns_45_names():
    s = pretrip.stations()
    assert len(s) == 45
    assert s[0] == "กรุงเทพอภิวัฒน์"
    assert s[-1] == "ยะลา"


def test_predict_rejects_past_date():
    last = pretrip._load_matrix().index.max()
    with pytest.raises(ValueError):
        pretrip.predict(last, station_idx=0)


def test_predict_rejects_too_far_ahead():
    last = pretrip._load_matrix().index.max()
    far = last + pd.Timedelta(days=pretrip.HORIZON + 1)
    with pytest.raises(ValueError):
        pretrip.predict(far, station_idx=0)


@pytest.mark.slow
def test_predict_returns_band():
    if not pretrip.RESIDUALS_PATH.exists():
        pytest.skip("Residuals not generated yet")
    last = pretrip._load_matrix().index.max()
    target = last + pd.Timedelta(days=1)
    p = pretrip.predict(target, station_idx=0)
    assert p.station_idx == 0
    assert p.p05 <= p.p50 <= p.p95
    assert p.target_date == target
