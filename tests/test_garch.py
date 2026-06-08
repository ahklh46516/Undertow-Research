"""Tests for the GARCH(1,1) volatility estimator."""

import numpy as np

from engine.garch import fit_vol


def _simulate_garch(n=1500, omega=2e-6, alpha=0.08, beta=0.90, seed=0):
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    h = omega / (1 - alpha - beta)
    for t in range(1, n):
        h = omega + alpha * r[t - 1] ** 2 + beta * h
        r[t] = rng.normal(scale=np.sqrt(h))
    return r


def test_output_shape_and_positivity():
    r = _simulate_garch()
    vol = fit_vol(r)
    assert vol.shape == (len(r),)
    assert np.all(vol > 0)
    assert np.all(np.isfinite(vol))


def test_tracks_volatility_clustering():
    r = _simulate_garch()
    vol = fit_vol(r)
    # periods of large |returns| should coincide with higher fitted vol
    big = np.abs(r) > np.quantile(np.abs(r), 0.9)
    assert vol[big].mean() > vol[~big].mean()


def test_handles_degenerate_input():
    assert np.all(fit_vol(np.zeros(50)) >= 0)
    assert len(fit_vol(np.ones(10))) == 10
