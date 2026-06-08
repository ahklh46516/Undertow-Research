# Methodology

This document describes how the Undertow engine turns raw market data into the
**Macro Undertow Index** and the **risk regime**. It is intentionally explicit about
being a *first-cut* model — a transparent baseline, not the full DCC-GARCH + hidden
Markov estimator described in the whitepaper.

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

## 2. Conditional correlation

The current correlation matrix `R_t` is the sample correlation over the trailing
`CORR_WINDOW` (default 90) days. The **mean pairwise correlation** `ρ̄(t)` is the mean
of the upper triangle of the trailing-`RHO_WINDOW` (default 60) day correlation,
computed per day — it rises toward one when the market sells off as a bloc.

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

## 4. Regime and probabilities

The regime is a threshold on the index:

| Index    | Regime    |
|----------|-----------|
| ≥ 60     | Risk-On   |
| 40 – 60  | Neutral   |
| < 40     | Risk-Off  |

State **probabilities** are a soft (softmax) function of the distance from each
regime's center (78 / 50 / 22), so they vary smoothly and sum to one. The empirical
**transition matrix** is estimated by counting day-to-day regime transitions.

## 5. Per-asset beta

Each asset's sensitivity to the tide is the slope of its returns regressed on the daily
change of the index, normalized so that SPX ≈ 1. Crypto typically shows the largest
betas; gold and the dollar are the smallest or negative.

## 6. Known limitations

- The index is a **percentile rank within its own window**, so it is relative, not
  absolute, and re-bases as the window rolls.
- The regime is threshold-based, not a fitted hidden-Markov model; probabilities are a
  heuristic, not posterior state probabilities.
- Correlation is not causation; past behavior does not guarantee future results.

Upgrading §3–4 to a proper DCC-GARCH + Baum-Welch/Viterbi estimator is the main planned
methodology improvement.
