"""A small Gaussian hidden Markov model with diagonal covariance.

Pure NumPy + SciPy implementation of Baum-Welch (EM) fitting and Viterbi decoding —
enough to estimate a handful of market regimes from a feature panel, without an
external HMM dependency. All recursions run in log-space (``logsumexp``) for numerical
stability.
"""

import numpy as np
from scipy.special import logsumexp

_LOG2PI = np.log(2.0 * np.pi)
_MIN_VAR = 1e-6


def _log_gaussian(X, means, covars):
    """Log N(x_t; mu_k, diag(cov_k)) for every (t, k). Returns (T, K)."""
    T, D = X.shape
    K = means.shape[0]
    out = np.empty((T, K))
    for k in range(K):
        diff = X - means[k]
        var = covars[k]
        out[:, k] = -0.5 * (D * _LOG2PI + np.sum(np.log(var)) + np.sum(diff * diff / var, axis=1))
    return out


class GaussianHMM:
    """Diagonal-covariance Gaussian HMM fit by Baum-Welch."""

    def __init__(self, n_states=3, n_iter=150, tol=1e-4):
        self.K = n_states
        self.n_iter = n_iter
        self.tol = tol

    # -- initialization (deterministic: split data by the first feature) --
    def _init(self, X):
        T, D = X.shape
        K = self.K
        order = np.argsort(X[:, 0])
        means = np.empty((K, D))
        covars = np.empty((K, D))
        for k, idx in enumerate(np.array_split(order, K)):
            means[k] = X[idx].mean(axis=0)
            covars[k] = X[idx].var(axis=0) + _MIN_VAR
        self.startprob = np.full(K, 1.0 / K)
        self.transmat = np.full((K, K), 1.0 / K)
        self.means = means
        self.covars = covars

    def fit(self, X):
        X = np.asarray(X, float)
        T, D = X.shape
        self._init(X)
        prev_ll = -np.inf
        for it in range(self.n_iter):
            flp = _log_gaussian(X, self.means, self.covars)        # (T, K)
            log_A = np.log(self.transmat + 1e-300)
            log_pi = np.log(self.startprob + 1e-300)

            # forward
            log_alpha = np.empty((T, self.K))
            log_alpha[0] = log_pi + flp[0]
            for t in range(1, T):
                log_alpha[t] = flp[t] + logsumexp(log_alpha[t - 1][:, None] + log_A, axis=0)
            ll = logsumexp(log_alpha[-1])

            # backward
            log_beta = np.zeros((T, self.K))
            for t in range(T - 2, -1, -1):
                log_beta[t] = logsumexp(log_A + flp[t + 1][None, :] + log_beta[t + 1][None, :], axis=1)

            # posteriors
            log_gamma = log_alpha + log_beta - ll
            gamma = np.exp(log_gamma)
            gamma /= gamma.sum(1, keepdims=True)

            # transition expectations
            xi_sum = np.zeros((self.K, self.K))
            for t in range(T - 1):
                log_xi = (log_alpha[t][:, None] + log_A
                          + flp[t + 1][None, :] + log_beta[t + 1][None, :] - ll)
                xi_sum += np.exp(log_xi)

            # M-step
            self.startprob = gamma[0] / gamma[0].sum()
            self.transmat = xi_sum / xi_sum.sum(1, keepdims=True)
            w = gamma.sum(0)
            self.means = (gamma.T @ X) / w[:, None]
            for k in range(self.K):
                diff = X - self.means[k]
                self.covars[k] = (gamma[:, k][:, None] * diff * diff).sum(0) / w[k] + _MIN_VAR

            if it > 0 and abs(ll - prev_ll) < self.tol:
                break
            prev_ll = ll

        self.loglik_ = ll
        return self

    def predict_proba(self, X):
        """Smoothed state posteriors gamma (T, K)."""
        X = np.asarray(X, float)
        T = X.shape[0]
        flp = _log_gaussian(X, self.means, self.covars)
        log_A = np.log(self.transmat + 1e-300)
        log_pi = np.log(self.startprob + 1e-300)
        log_alpha = np.empty((T, self.K))
        log_alpha[0] = log_pi + flp[0]
        for t in range(1, T):
            log_alpha[t] = flp[t] + logsumexp(log_alpha[t - 1][:, None] + log_A, axis=0)
        ll = logsumexp(log_alpha[-1])
        log_beta = np.zeros((T, self.K))
        for t in range(T - 2, -1, -1):
            log_beta[t] = logsumexp(log_A + flp[t + 1][None, :] + log_beta[t + 1][None, :], axis=1)
        gamma = np.exp(log_alpha + log_beta - ll)
        return gamma / gamma.sum(1, keepdims=True)

    def decode(self, X):
        """Most likely state path (Viterbi). Returns an int array of length T."""
        X = np.asarray(X, float)
        T = X.shape[0]
        flp = _log_gaussian(X, self.means, self.covars)
        log_A = np.log(self.transmat + 1e-300)
        log_pi = np.log(self.startprob + 1e-300)
        delta = np.empty((T, self.K))
        psi = np.zeros((T, self.K), dtype=int)
        delta[0] = log_pi + flp[0]
        for t in range(1, T):
            scores = delta[t - 1][:, None] + log_A
            psi[t] = np.argmax(scores, axis=0)
            delta[t] = flp[t] + np.max(scores, axis=0)
        path = np.empty(T, dtype=int)
        path[-1] = int(np.argmax(delta[-1]))
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]
        return path
