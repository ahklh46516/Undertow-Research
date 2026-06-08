"""Orchestrate the pipeline: fetch -> model -> write outputs.

Writes ``web/data.json`` (consumed by the dashboard) and re-renders
``web/assets/heatmap.svg`` from the real correlation matrix.
"""

import json
from pathlib import Path

from . import sources, model, heatmap

ROOT = Path(__file__).resolve().parent.parent
DATA_OUT = ROOT / "web" / "data.json"
HEATMAP_OUT = ROOT / "web" / "assets" / "heatmap.svg"


def run():
    """Fetch live data, compute the model, write outputs, and return the data dict."""
    price_df, tnx = sources.fetch_panel()
    data, asset_names, corr = model.compute(price_df, tnx)
    DATA_OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    HEATMAP_OUT.write_text(heatmap.render(asset_names, corr), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = run()
    print("wrote %s\n  as_of=%s  index=%s  regime=%s  rho=%.2f"
          % (DATA_OUT, d["as_of"], d["index"], d["regime"], d["rho_bar"]))
