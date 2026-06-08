# Contributing to Undertow

Thanks for your interest in Undertow. This is an early-stage research project — issues,
ideas, and pull requests are all welcome.

## Ways to contribute

- **Methodology** — improvements to the regime/index model (e.g. a proper DCC-GARCH +
  hidden-Markov estimator to replace the first-cut heuristic).
- **Data sources** — additional assets, more robust ingestion, better alignment.
- **Frontend** — the whitepaper (`web/index.html`) and dashboard (`web/terminal.html`).
- **Docs** — anything in `docs/`.

## Project layout

```
engine/   Python data pipeline (sources, model, heatmap, pipeline)
web/      Static site: whitepaper, dashboard, assets, data.json
docs/     Methodology and architecture notes
```

## Development

```bash
pip install -r requirements.txt
python -m engine.pipeline        # fetch data + recompute web/data.json
python -m http.server 8777 --directory web
```

Then open <http://localhost:8777/index.html> (whitepaper) or
<http://localhost:8777/terminal.html> (dashboard).

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Keep changes focused; match the existing style (the engine has no heavy
   dependencies beyond `pandas`/`numpy`, and the frontend is dependency-free).
3. If you change the model, update `docs/methodology.md`.
4. Open a PR describing **what** changed and **why**.

## A note on scope

Undertow is research, not investment advice. Please keep contributions honest about
the limits of the model — no implied guarantees of returns, and no claims that the
on-chain oracle is live (it is not yet deployed).
