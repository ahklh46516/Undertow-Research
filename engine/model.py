"""The Undertow statistical model.

Given an aligned panel of prices, computes everything the dashboard needs:

- the conditional (trailing-window) correlation matrix,
- the rolling mean pairwise correlation,
- the composite Macro Undertow Index (0-100),
- the risk regime and its probabilities,
- per-asset beta to the index,
- the regime transition matrix and per-regime statistics,
- the liquidity drivers, the index time series, the recent feed and history.

Nothing here forecasts prices. The regime/index are a transparent, first-cut model
over real market data.
"""

import numpy as np
import pandas as pd

from .sources import ASSET_NAMES, RISK

LABELS = ["Risk-On", "Neutral", "Risk-Off"]
CORR_WINDOW = 90      # trailing days for the current correlation matrix
RHO_WINDOW = 60       # trailing days for rolling mean correlation
MOM_WINDOW = 20       # momentum / vol / dollar lookback


def _regime_of(v):
    return "Risk-On" if v >= 60 else ("Neutral" if v >= 40 else "Risk-Off")


def _probs_of(v):
    """Soft state probabilities from the index value (heuristic, sums to 1)."""
    centers = {"Risk-On": 78, "Neutral": 50, "Risk-Off": 22}
    logits = {k: -abs(v - c) / 18.0 for k, c in centers.items()}
    m = max(logits.values())
    exp = {k: np.exp(x - m) for k, x in logits.items()}
    s = sum(exp.values())
    return {k: exp[k] / s for k in exp}


def _pct(series, n):
    return float(series.iloc[-1] / series.iloc[-1 - n] - 1) * 100 if len(series) > n else 0.0


def _rolling_mean_corr(returns):
    """Mean of the upper-triangle of the trailing-window correlation, per day."""
    vals = returns[ASSET_NAMES].values
    dates = list(returns.index)
    win = min(RHO_WINDOW, len(returns))
    out, idx = [], []
    for i in range(win, len(returns) + 1):
        c = np.corrcoef(vals[i - win:i], rowvar=False)
        iu = np.triu_indices(c.shape[0], 1)
        out.append(float(np.nanmean(c[iu])))
        idx.append(dates[i - 1])
    return pd.Series(out, index=idx)


def compute(price_df, tnx=None):
    """Run the model. Returns ``(data_dict, asset_names, corr_matrix)``."""
    px = price_df
    ret = np.log(px / px.shift(1)).dropna()
    as_of = px.index[-1]

    # ---- conditional correlation (trailing window) ----
    window = min(CORR_WINDOW, len(ret))
    rt = ret.tail(window).corr().reindex(index=ASSET_NAMES, columns=ASSET_NAMES)
    corr = rt.values
    rho_series = _rolling_mean_corr(ret)
    rho_bar = float(rho_series.iloc[-1])

    # ---- composite Macro Undertow Index ----
    risk_ret = ret[RISK].mean(axis=1)
    mom = risk_ret.rolling(MOM_WINDOW).sum()
    vol = risk_ret.rolling(MOM_WINDOW).std()
    dxy_chg = np.log(px["DXY"] / px["DXY"].shift(MOM_WINDOW))   # dollar up = risk-off
    rho_aligned = rho_series.reindex(ret.index)
    feat = pd.DataFrame({"mom": mom, "vol": vol, "dxy": dxy_chg, "rho": rho_aligned}).dropna()
    z = (feat - feat.mean()) / feat.std()
    score = z["mom"] - z["dxy"] - z["rho"] - z["vol"]
    index = (score.rank(pct=True) * 100.0).dropna()
    reg_series = index.apply(_regime_of)

    cur_index = float(index.iloc[-1])
    cur_regime = _regime_of(cur_index)
    cur_probs = _probs_of(cur_index)

    # ---- per-asset beta to dIndex (normalized to SPX = 1) ----
    d_index = (index / 100.0).diff()
    aligned_ret = ret.reindex(index.index)
    raw = {}
    for a in ASSET_NAMES:
        x, y = d_index.values, aligned_ret[a].values
        msk = ~np.isnan(x) & ~np.isnan(y)
        raw[a] = float(np.polyfit(x[msk], y[msk], 1)[0]) if msk.sum() > 10 else 0.0
    spx_b = raw.get("SPX", 1.0) or 1.0
    betas = sorted([[a, round(b / abs(spx_b), 1)] for a, b in raw.items()], key=lambda r: -r[1])

    # ---- transition matrix ----
    idx_of = {l: i for i, l in enumerate(LABELS)}
    t = np.zeros((3, 3))
    seq = reg_series.values
    for i in range(len(seq) - 1):
        t[idx_of[seq[i]], idx_of[seq[i + 1]]] += 1
    t = np.divide(t, t.sum(1, keepdims=True), out=np.zeros_like(t), where=t.sum(1, keepdims=True) != 0)
    transition = [[round(float(x), 2) for x in row] for row in t]

    # ---- per-regime statistics ----
    runs, prev, cnt = [], None, 0
    for r in seq:
        if r == prev:
            cnt += 1
        else:
            if prev is not None:
                runs.append((prev, cnt))
            prev, cnt = r, 1
    if prev is not None:
        runs.append((prev, cnt))
    regime_stats = {}
    for lab in LABELS:
        days = reg_series[reg_series == lab].index
        durs = [c for l, c in runs if l == lab]
        regime_stats[lab] = {
            "rho": round(float(rho_aligned.reindex(days).mean()) if len(days) else 0.0, 2),
            "vol": round(float(risk_ret.reindex(days).std() * np.sqrt(252) * 100) if len(days) > 1 else 0.0),
            "share": round(len(days) / len(reg_series) * 100),
            "dur": round(float(np.mean(durs)), 1) if durs else 0,
        }

    # ---- liquidity drivers (real) ----
    dxy_now, dxy_20 = float(px["DXY"].iloc[-1]), _pct(px["DXY"], 20)
    btc_30 = _pct(px["BTC"], 30)
    rb_vol = float(vol.iloc[-1] * np.sqrt(252) * 100)
    drivers = [
        {"k": "Dollar index (DXY)", "v": "%.1f" % dxy_now, "tone": "bad" if dxy_20 > 0 else "good",
         "note": ("tightening" if dxy_20 > 0 else "easing") + " (%+.1f%% 20d)" % dxy_20},
        {"k": "Risk basket 20d", "v": "%+.1f%%" % (float(mom.iloc[-1]) * 100),
         "tone": "good" if mom.iloc[-1] > 0 else "bad", "note": "BTC, ETH, SPX, NDX, KOSPI"},
        {"k": "BTC 30d momentum", "v": "%+.1f%%" % btc_30, "tone": "good" if btc_30 > 0 else "bad",
         "note": "trailing 30 sessions"},
        {"k": "Realized vol (ann.)", "v": "%.0f%%" % rb_vol, "tone": "neu", "note": "risk basket"},
        {"k": "Mean pairwise correlation", "v": "%.2f" % rho_bar,
         "tone": "bad" if rho_bar > 0.4 else "good", "note": "elevated" if rho_bar > 0.4 else "calm / dispersed"},
    ]
    if tnx is not None and len(tnx) > 21:
        y_now = float(tnx.iloc[-1])
        y_20 = float(tnx.iloc[-1]) - float(tnx.iloc[-21])
        drivers.insert(1, {"k": "10y Treasury yield", "v": "%.2f%%" % y_now,
                           "tone": "bad" if y_20 > 0 else "good",
                           "note": ("rising" if y_20 > 0 else "falling") + " (%+.2f 20d)" % y_20})

    # ---- chart series ----
    rho_for_chart = rho_aligned.reindex(index.index).clip(0, 1) * 100
    chart = {
        "dates": list(index.index),
        "index": [round(float(v), 1) for v in index.values],
        "rho": [round(float(v), 1) for v in rho_for_chart.values],
        "regime": [_regime_of(v) for v in index.values],
    }

    # ---- recent feed (last 6) ----
    feed = []
    for d in list(index.index)[-6:][::-1]:
        v = float(index.loc[d])
        feed.append({"date": d, "regime": _regime_of(v), "index": round(v),
                     "pon": round(_probs_of(v)["Risk-On"], 2)})

    # ---- 36-week regime history ----
    weekly = reg_series.iloc[::-5][::-1].tail(36)
    hmap = {"Risk-On": "o", "Neutral": "n", "Risk-Off": "g"}
    history = [hmap[r] for r in weekly.values]

    data = {
        "as_of": as_of,
        "window_days": int(window),
        "index": round(cur_index),
        "index_exact": round(cur_index, 1),
        "regime": cur_regime,
        "probs": {"on": round(cur_probs["Risk-On"], 2),
                  "neutral": round(cur_probs["Neutral"], 2),
                  "off": round(cur_probs["Risk-Off"], 2)},
        "rho_bar": round(rho_bar, 2),
        "drivers": drivers,
        "betas": betas,
        "assets": ASSET_NAMES,
        "corr": [[round(float(x), 2) for x in row] for row in corr],
        "transition": transition,
        "regime_stats": regime_stats,
        "history": history,
        "feed": feed,
        "chart": chart,
        "prices": {a: round(float(px[a].iloc[-1]), 2) for a in ASSET_NAMES},
    }
    return data, ASSET_NAMES, corr
