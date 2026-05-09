import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml import live_eta


@pytest.fixture(autouse=True)
def _require_model():
    if not live_eta.MODEL_PATH.exists():
        pytest.skip(
            "live_eta_model.pkl not present — run `python3 -m ml.train` to generate it."
        )


def test_predict_returns_ordered_band():
    p = live_eta.predict(cur_idx=0, cur_delay=10.0, tgt_idx=20, today=date(2026, 5, 9))
    assert p.target_idx == 20
    assert p.p05 <= p.p50 <= p.p95


def test_predict_rejects_backward_target():
    with pytest.raises(ValueError):
        live_eta.predict(cur_idx=10, cur_delay=5.0, tgt_idx=5, today=date(2026, 5, 9))


def test_predict_remaining_returns_full_chain():
    preds = live_eta.predict_remaining(
        cur_idx=0,
        cur_delay=15.0,
        n_stations=45,
        today=date(2026, 5, 9),
    )
    assert len(preds) == 44
    assert [p.target_idx for p in preds] == list(range(1, 45))


def test_predict_consistency_seasonal():
    """Predicted band width should generally widen further down the line (more uncertainty)."""
    preds = live_eta.predict_remaining(
        cur_idx=0,
        cur_delay=5.0,
        n_stations=45,
        today=date(2026, 5, 9),
    )
    near_width = preds[0].p95 - preds[0].p05
    far_width = preds[-1].p95 - preds[-1].p05
    assert far_width > near_width
