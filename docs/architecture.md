# Architecture

Undertow has two halves: an **off-chain engine** that computes the macro state, and a
**static frontend** that presents it. They are decoupled by a single JSON artifact.

```
                          ┌──────────────────────────────────────────┐
   Yahoo Finance  ──────▶ │  engine/  (Python)                       │
   (daily closes)         │   sources.py   fetch & align the panel   │
                          │   model.py     correlation, index,       │
                          │                regime, betas, ...        │
                          │   heatmap.py   render correlation SVG     │
                          │   pipeline.py  orchestrate + write        │
                          └───────────────┬──────────────────────────┘
                                          │ writes
                                          ▼
                          web/data.json   +   web/assets/heatmap.svg
                                          │
                                          │ fetched every 45s
                                          ▼
                          ┌──────────────────────────────────────────┐
   browser  ◀──────────── │  web/  (static, dependency-free)         │
                          │   index.html      whitepaper             │
                          │   terminal.html   live dashboard         │
                          │   assets/         logo, favicons, svg    │
                          └──────────────────────────────────────────┘
```

## Data contract (`web/data.json`)

The engine writes a single JSON object; the dashboard reads it. Key fields:

| Field           | Meaning                                              |
|-----------------|------------------------------------------------------|
| `as_of`         | UTC date of the latest close                         |
| `index`         | Macro Undertow Index, 0–100                          |
| `regime`        | `Risk-On` / `Neutral` / `Risk-Off`                   |
| `probs`         | state probabilities                                  |
| `rho_bar`       | mean pairwise correlation                            |
| `corr`          | N×N conditional correlation matrix                   |
| `betas`         | per-asset beta to the index                          |
| `transition`    | 3×3 regime transition matrix                         |
| `regime_stats`  | per-regime ρ̄ / vol / share / duration               |
| `drivers`       | liquidity drivers (DXY, yield, momentum, vol, ρ̄)     |
| `chart`         | index / ρ̄ / regime time series                       |
| `feed`          | recent per-epoch reports                             |
| `history`       | 36-week regime sequence                              |

## Refresh paths

- **Local:** `python -m engine.live_update` re-runs the pipeline every ~2 minutes.
- **CI:** `.github/workflows/refresh-data.yml` runs the pipeline on a schedule and
  commits the refreshed `data.json` / `heatmap.svg`.
- **Browser:** the dashboard polls `data.json` every 45 seconds, so an updated file
  appears without a manual refresh.

## Future (not built)

The whitepaper describes an on-chain oracle that would publish the regime/index as a
verifiable primitive (staked optimistic reporting). It is **not deployed**; the Oracle
Dashboard view labels those fields as testnet placeholders.
