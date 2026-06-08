"""Undertow P0 engine.

Fetches real cross-asset market data and computes the macro state of the world —
a cross-asset risk regime and a composite liquidity index — then writes the result
to ``web/data.json`` (consumed by the dashboard) and re-renders the correlation
heatmap.

Modules
-------
sources : market-data ingestion (Yahoo Finance chart API)
model   : the statistical model (correlation, index, regime, betas, ...)
heatmap : renders the conditional-correlation matrix to an SVG
pipeline: orchestrates fetch -> model -> write
"""

__version__ = "0.1.0"
