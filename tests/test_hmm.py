"""Tests for the hand-rolled Gaussian HMM."""

import numpy as np

from engine.hmm import GaussianHMM


def _synthetic_two_state(n=600, seed=0):
    """Sticky two-state series with well-separated Gaussian emissions."""
    rng = np.random.default_rng(seed)
    A = np.array([[0.97, 0.03], [0.03, 0.97]])
    means = np.array([[-2.0, -2.0], [2.0, 2.0]])
    states, s = [], 0
    for _ in range(n):
        s = rng.choice(2, p=A[s])
        states.append(s)
    states = np.array(states)
    X = means[states] + rng.normal(scale=0.4, size=(n, 2))
    return X, states


def test_probabilities_are_valid():
    X, _ = _synthetic_two_state()
    hmm = GaussianHMM(n_states=2).fit(X)
    post = hmm.predict_proba(X)
    assert post.shape == (len(X), 2)
    assert np.allclose(post.sum(axis=1), 1.0, atol=1e-6)
    assert np.isfinite(hmm.loglik_)


def test_recovers_two_states():
    X, states = _synthetic_two_state()
    hmm = GaussianHMM(n_states=2).fit(X)
    path = hmm.decode(X)
    # the decoded path should match the true states up to a label swap
    acc = max((path == states).mean(), (path != states).mean())
    assert acc > 0.9


def test_transition_rows_sum_to_one():
    X, _ = _synthetic_two_state()
    hmm = GaussianHMM(n_states=2).fit(X)
    assert np.allclose(hmm.transmat.sum(axis=1), 1.0, atol=1e-6)
    # sticky chain -> strong diagonal
    assert np.all(np.diag(hmm.transmat) > 0.8)
