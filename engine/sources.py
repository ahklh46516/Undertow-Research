"""Market-data ingestion.

Pulls ~1 year of daily closes for the cross-asset panel from the public Yahoo
Finance chart API. No API key is required. Each fetch retries a few times to ride
out transient network hiccups.
"""

import urllib.request
import urllib.parse
import json
import datetime
import time

import pandas as pd

HDR = {"User-Agent": "Mozilla/5.0"}

# (display name, Yahoo symbol)
ASSETS = [
    ("BTC", "BTC-USD"),
    ("ETH", "ETH-USD"),
    ("SPX", "^GSPC"),
    ("Nasdaq", "^IXIC"),
    ("KOSPI", "^KS11"),
    ("Gold", "GC=F"),
    ("Oil", "CL=F"),
    ("DXY", "DX-Y.NYB"),
]

# assets that make up the "risk basket" used by the index
RISK = ["BTC", "ETH", "SPX", "Nasdaq", "KOSPI"]

ASSET_NAMES = [name for name, _ in ASSETS]

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval={interval}"


def fetch_series(symbol, rng="1y", interval="1d", tries=3):
    """Return a UTC-date-indexed ``pandas.Series`` of closes for one Yahoo symbol."""
    url = _CHART_URL.format(sym=urllib.parse.quote(symbol), rng=rng, interval=interval)
    last_err = None
    for _ in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25).read()
            res = json.loads(raw)["chart"]["result"][0]
            closes = {}
            for ts, close in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
                if close is None:
                    continue
                day = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")
                closes[day] = close
            return pd.Series(closes)
        except Exception as err:  # noqa: BLE001 - retry on any transient failure
            last_err = err
            time.sleep(1.5)
    raise last_err


def fetch_panel():
    """Fetch the whole panel plus the 10y Treasury yield.

    Returns ``(price_df, tnx_series_or_None)`` where ``price_df`` is aligned to the
    common set of trading days across all assets.
    """
    prices = {name: fetch_series(sym) for name, sym in ASSETS}
    try:
        tnx = fetch_series("^TNX")  # 10y Treasury yield (percent)
    except Exception:  # noqa: BLE001 - the yield is an optional driver
        tnx = None
    price_df = pd.DataFrame(prices).sort_index().dropna()
    return price_df, tnx
