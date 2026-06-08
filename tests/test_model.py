"""Integration smoke test for the full model on synthetic prices (no network)."""

import numpy as np
import pandas as pd

from engine.sources import ASSET_NAMES
from engine import model


def _synthetic_prices(n=320, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=n, freq="D").strftime("%Y-%m-%d")
    cols = {}
    for a in ASSET_NAMES:
        steps = rng.normal(0, 0.02, size=n)
        cols[a] = 100 * np.exp(np.cumsum(steps))
    return pd.DataFrame(cols, index=dates)


def test_compute_contract():
    px = _synthetic_prices()
    data, names, corr = model.compute(px)

    for key in ("index", "regime", "probs", "corr", "transition", "betas",
                "chart", "feed", "history", "regime_stats", "model"):
        assert key in data

    assert 0 <= data["index"] <= 100
    assert data["regime"] in model.LABELS
    assert abs(sum(data["probs"].values()) - 1.0) < 1e-6
    assert data["model"] in ("hmm", "threshold")


def test_correlation_matrix_shape():
    px = _synthetic_prices()
    data, names, corr = model.compute(px)
    n = len(ASSET_NAMES)
    assert np.array(corr).shape == (n, n)
    # unit diagonal
    assert np.allclose(np.diag(np.array(corr)), 1.0, atol=1e-6)


def test_transition_rows_sum_to_one():
    px = _synthetic_prices()
    data, _, _ = model.compute(px)
    for row in data["transition"]:
        assert abs(sum(row) - 1.0) < 0.02 or sum(row) == 0
