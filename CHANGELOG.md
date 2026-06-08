# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-06-08

First public research preview.

### Engine
- Cross-asset data pipeline (Yahoo Finance) as a modular Python package —
  `sources`, `model`, `heatmap`, `pipeline`, `live_update`.
- Conditional correlation matrix, mean pairwise correlation, a composite
  **Macro Undertow Index** (0–100), per-asset **betas**, and per-regime statistics.
- A 3-state Gaussian **hidden Markov regime** (Baum-Welch fit, Viterbi decode, log-space
  forward-backward) and a maximum-likelihood **GARCH(1,1)** volatility estimator —
  both implemented from scratch in NumPy/SciPy, with a threshold fallback.

### Frontend
- Whitepaper (`web/index.html`) with original SVG figures (correlation heatmap, HMM state
  machine, correlation network, index time series).
- **Undertow Terminal** dashboard (`web/terminal.html`) with three views — Terminal,
  Regime Explorer, Oracle Dashboard — driven by computed data and auto-refreshing.

### Tooling
- `pytest` suite (HMM, GARCH, full-model contract) and CI on Python 3.10 & 3.12.
- GitHub Actions for scheduled data refresh and GitHub Pages deployment.
- Docs (methodology, architecture), MIT license, contributing guide, code of conduct,
  security policy, and issue/PR templates.

### Notes
- The regime/index are computed from real market data; the on-chain oracle is **not yet
  deployed**.
- Research only — not financial advice.

[0.1.0]: https://github.com/nickbauman77/Undertow-Research/releases/tag/v0.1.0
