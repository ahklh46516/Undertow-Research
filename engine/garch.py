"""GARCH(1,1) conditional volatility.

A compact maximum-likelihood GARCH(1,1) estimator (Gaussian innovations) using
``scipy.optimize``. Used to give the model a proper conditional-volatility series
instead of a plain rolling standard deviation.
"""

import numpy as np
from scipy.optimize import minimize


def _neg_loglik(params, r):
    omega, alpha, beta = params
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
        return 1e10
    n = len(r)
    h = np.empty(n)
    h[0] = r.var()
    for t in range(1, n):
        h[t] = omega + alpha * r[t - 1] ** 2 + beta * h[t - 1]
    h = np.maximum(h, 1e-12)
    return 0.5 * np.sum(np.log(2 * np.pi) + np.log(h) + r ** 2 / h)


def fit_vol(returns):
    """Fit GARCH(1,1) on a (demeaned) return series and return conditional volatility.

    Falls back to a rolling/EWMA-style estimate if the optimizer fails to converge.
    Returns a NumPy array of the same length as ``returns``.
    """
    r = np.asarray(returns, float)
    r = r - r.mean()
    var = r.var()
    if var == 0 or len(r) < 30:
        return np.full(len(r), np.sqrt(max(var, 1e-12)))

    x0 = [var * 0.05, 0.05, 0.90]
    bounds = [(1e-12, None), (0.0, 0.999), (0.0, 0.999)]
    try:
        res = minimize(_neg_loglik, x0, args=(r,), method="L-BFGS-B", bounds=bounds)
        omega, alpha, beta = res.x if res.success else x0
    except Exception:  # noqa: BLE001 - fall back to a sane EWMA-like estimate
        omega, alpha, beta = x0

    n = len(r)
    h = np.empty(n)
    h[0] = var
    for t in range(1, n):
        h[t] = omega + alpha * r[t - 1] ** 2 + beta * h[t - 1]
    return np.sqrt(np.maximum(h, 1e-12))
