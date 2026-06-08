# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- **Real model.** Replaced the threshold/heuristic regime with a hand-rolled
  3-state Gaussian **hidden Markov model** (Baum-Welch fit, Viterbi decode, log-space
  forward-backward) and added a maximum-likelihood **GARCH(1,1)** volatility estimator.
  Regime, posterior probabilities and the transition matrix are now model outputs.
  Falls back to the threshold method if the HMM fails to fit.

### Added
- `engine/hmm.py`, `engine/garch.py`.
- `tests/` — pytest suite for the HMM, GARCH and the full model contract, plus a CI
  test workflow (`.github/workflows/tests.yml`).

## [0.1.0] — 2026-06

### Added
- Whitepaper (`web/index.html`): the cross-asset macro thesis, model, oracle design,
  and fair-launch token positioning, with original SVG figures (correlation heatmap,
  HMM state machine, correlation network, index time series).
- Undertow Terminal (`web/terminal.html`): a live dashboard with three views —
  Terminal (overview), Regime Explorer, and Oracle Dashboard — driven entirely by
  computed data and auto-refreshing from `data.json`.
- P0 engine (`engine/`): modular data pipeline that fetches real cross-asset prices,
  computes the conditional correlation matrix, a composite Macro Undertow Index, the
  risk regime and probabilities, per-asset betas, the transition matrix, and regime
  statistics.
- Scheduled data refresh via GitHub Actions.
- Project docs: methodology, architecture, contributing guide, code of conduct,
  security policy.

### Notes
- The regime/index are a first-cut model over real market data.
- The on-chain oracle is **not yet deployed**.
