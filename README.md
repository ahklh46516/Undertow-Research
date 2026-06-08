<div align="center">
  <img src="web/assets/logo.png" alt="Undertow" height="72" />
  <h1>Undertow</h1>
  <p><strong>The macro layer for on-chain markets.</strong></p>

  <p>
    <img alt="status" src="https://img.shields.io/badge/status-research_preview-e0a45c" />
    <img alt="license" src="https://img.shields.io/badge/license-MIT-34c75e" />
    <img alt="python" src="https://img.shields.io/badge/python-3.10%2B-4db6ac" />
    <img alt="model" src="https://img.shields.io/badge/model-HMM%20%2B%20GARCH-e8517f" />
    <img alt="data" src="https://img.shields.io/badge/data-live-34c75e" />
  </p>
</div>

---

Bitcoin, U.S. & Korean equities, gold, crude oil and the spot-crypto ETFs are not
independent — they breathe to the same rhythm: the expansion and contraction of global
dollar liquidity. What traders feel as a vague "everything is connected" is a single
underlying force pushing every risk asset in tandem and rotating capital between them as
a switch flips between **risk-on** and **risk-off**.

**Undertow measures that force.** It estimates the unobserved *macro state* of the world —
a cross-asset risk regime and a composite liquidity index — from real public market data,
and is designed to publish it on-chain as a verifiable primitive any application can
consume.

## Repository layout

```
.
├── engine/                 # Python data pipeline
│   ├── sources.py          #   fetch & align the cross-asset panel (Yahoo Finance)
│   ├── model.py            #   correlation, index, regime, betas, transitions
│   ├── hmm.py              #   Gaussian HMM (Baum-Welch + Viterbi)
│   ├── garch.py            #   GARCH(1,1) conditional volatility
│   ├── heatmap.py          #   render the correlation matrix to SVG
│   ├── pipeline.py         #   orchestrate: fetch -> model -> write
│   └── live_update.py      #   re-run on an interval
├── tests/                  # pytest suite (hmm, garch, model)
├── web/                    # static, dependency-free frontend
│   ├── index.html          #   the whitepaper
│   ├── terminal.html       #   the live dashboard (Terminal / Regime / Oracle)
│   ├── data.json           #   latest computed snapshot
│   └── assets/             #   logo, favicons, heatmap.svg
├── docs/                   # methodology & architecture
├── .github/                # CI (scheduled data refresh) + templates
├── requirements.txt
└── LICENSE
```

## Quickstart

```bash
pip install -r requirements.txt

# 1. compute a fresh snapshot (writes web/data.json + web/assets/heatmap.svg)
python -m engine.pipeline

# 2. serve the site
python -m http.server 8777 --directory web
```

Open:
- <http://localhost:8777/index.html> — the whitepaper
- <http://localhost:8777/terminal.html> — the dashboard

Keep data fresh locally with `python -m engine.live_update` (re-runs every ~2 min);
the dashboard polls `data.json` every 45s, so it updates without a manual refresh. In
CI, `.github/workflows/refresh-data.yml` refreshes the snapshot on a schedule.

## The model

The engine pulls ~1 year of daily closes for BTC, ETH, S&P 500, Nasdaq, KOSPI, gold,
WTI crude, the dollar index and the 10y Treasury yield, then computes:

- a conditional **correlation** matrix and **GARCH(1,1)** risk-basket volatility,
- a composite **Macro Undertow Index** (0–100) — a continuous liquidity gauge,
- the **risk regime** from a 3-state Gaussian **hidden Markov model** (Baum-Welch fit,
  Viterbi decode) with posterior state probabilities and an estimated transition matrix,
- per-asset **betas** and per-regime statistics.

The HMM and GARCH estimators are implemented from scratch in NumPy/SciPy. Full details in
[`docs/methodology.md`](docs/methodology.md); the data flow is in
[`docs/architecture.md`](docs/architecture.md).

Data source: public market data (Yahoo Finance chart API). No API key required.

## Status & disclaimers

This is a **research project under active development**. The model describes statistical
relationships, not certainties: *correlation is not causation, and past behavior does not
guarantee future results.* The regime/index are a first-cut model; the on-chain oracle is
**not yet deployed**. Nothing here is financial, investment, or legal advice, nor an offer
to buy or sell any security or token. See [`LICENSE`](LICENSE) (MIT).
