# Methodology

This document describes how the Undertow engine turns raw market data into the
**Macro Undertow Index** (a continuous liquidity gauge) and the **risk regime** (a
discrete hidden-Markov state). The regime is estimated with a real Baum-Welch / Viterbi
HMM and the volatility with a maximum-likelihood GARCH(1,1) — both implemented from
scratch in NumPy/SciPy (no `hmmlearn` / `arch` dependency).

## 1. Panel

Daily closes (~1 year) for:

| Class       | Assets                                  |
|-------------|-----------------------------------------|
| Crypto      | BTC, ETH                                |
| US equity   | S&P 500 (`^GSPC`), Nasdaq (`^IXIC`)     |
| Korea       | KOSPI (`^KS11`)                         |
| Commodity   | Gold (`GC=F`), WTI crude (`CL=F`)       |
| FX / macro  | Dollar index (`DX-Y.NYB`), 10y yield (`^TNX`) |

Source: the public Yahoo Finance chart API (`engine/sources.py`). All series are
aligned to the common set of trading days, then converted to log returns.

The **risk basket** is the equal-weight mean of BTC, ETH, SPX, Nasdaq and KOSPI.

## 2. Conditional correlation & volatility

The current correlation matrix `R_t` is the sample correlation over the trailing
`CORR_WINDOW` (default 90) days. The **mean pairwise correlation** `ρ̄(t)` is the mean
of the upper triangle of the trailing-`RHO_WINDOW` (default 60) day correlation,
computed per day — it rises toward one when the market sells off as a bloc.

The risk-basket **conditional volatility** is estimated with a **GARCH(1,1)** model
(`engine/garch.py`), fit by maximum likelihood under Gaussian innovations:

```
h_t = ω + α·r_{t-1}² + β·h_{t-1}
```

with `ω > 0`, `α, β ≥ 0`, `α + β < 1`. This replaces a plain rolling standard deviation
and feeds both the regime model and the volatility driver.

## 3. Macro Undertow Index

For each day we form four standardized (z-scored over the sample) features:

- `mom` — 20-day sum of risk-basket returns (momentum, **+**),
- `dxy` — 20-day log change of the dollar index (**−**, a stronger dollar is risk-off),
- `rho` — mean pairwise correlation (**−**, contagion),
- `vol` — 20-day realized volatility of the risk basket (**−**).

The composite score is

```
score = z(mom) − z(dxy) − z(rho) − z(vol)
```

and the index is its percentile rank over the sample, scaled to `[0, 100]`:

```
Index(t) = 100 · percentile_rank( score(t) )
```

## 4. Regime: a hidden Markov model

The regime is the hidden state of a **3-state Gaussian HMM** (`engine/hmm.py`) fit on a
daily feature panel:

```
features = [ risk-basket momentum (20d) , mean pairwise correlation ,
             GARCH volatility , dollar 20d change ]   (standardized)
```

- Parameters (start probabilities `π`, transition matrix `A`, per-state Gaussian means
  and diagonal covariances) are estimated by **Baum-Welch** (EM) with log-space
  forward-backward for numerical stability.
- The most likely state path is decoded with **Viterbi**; the current state's
  **posterior probabilities** come from the forward-backward smoother.
- States are labelled post-hoc by a risk score on their means
  (`mean(mom) − mean(ρ̄) − mean(vol) − mean(dxy)`): highest → Risk-On, lowest → Risk-Off.
- The **transition matrix** shown in the dashboard is the HMM's estimated `A`.

If the HMM fails to fit (degenerate data), the engine falls back to a transparent
threshold on the index (≥60 Risk-On, 40–60 Neutral, <40 Risk-Off) so the pipeline never
breaks. The `model` field in `data.json` records which path was used (`hmm` / `threshold`).

The **index** and the **regime** are deliberately separate: the index is a continuous
percentile gauge of liquidity/risk appetite, the regime is the HMM's discrete state.
They usually agree, but can diverge (e.g. a low gauge while volatility is not yet in the
rare crash state) — which is informative, not a bug.

## 5. Per-asset beta

Each asset's sensitivity to the tide is the slope of its returns regressed on the daily
change of the index, normalized so that SPX ≈ 1. Crypto typically shows the largest
betas; gold and the dollar are the smallest or negative.

## 6. Known limitations

- The index is a **percentile rank within its own window**, so it is relative, not
  absolute, and re-bases as the window rolls.
- The HMM uses **diagonal** covariances and a small fixed number of states; correlation
  is still a rolling-window estimate rather than a full **DCC-GARCH** dynamic
  correlation. That dynamic-correlation upgrade is the main remaining model improvement.
- ~1 year of daily history is a short sample for estimating regime transitions.
- Correlation is not causation; past behavior does not guarantee future results.
