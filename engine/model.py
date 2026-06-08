"""The Undertow statistical model.

Given an aligned panel of prices, computes everything the dashboard needs:

- the conditional (trailing-window) correlation matrix and rolling mean correlation,
- GARCH(1,1) conditional volatility of the risk basket,
- a 3-state Gaussian **hidden Markov regime** (Baum-Welch fit, Viterbi decode) with
  posterior state probabilities and an estimated transition matrix,
- a composite Macro Undertow Index (0-100) as a continuous liquidity gauge,
- per-asset beta to the index, and per-regime statistics.

Nothing here forecasts prices. If the HMM fails to fit (degenerate data), the regime
falls back to a transparent threshold on the index so the pipeline never breaks.
"""

import numpy as np
import pandas as pd

from .sources import ASSET_NAMES, RISK
from .hmm import GaussianHMM
from .garch import fit_vol

LABELS = ["Risk-On", "Neutral", "Risk-Off"]
CORR_WINDOW = 90
RHO_WINDOW = 60
MOM_WINDOW = 20


def _regime_of(v):
    return "Risk-On" if v >= 60 else ("Neutral" if v >= 40 else "Risk-Off")


def _probs_of(v):
    centers = {"Risk-On": 78, "Neutral": 50, "Risk-Off": 22}
    logits = {k: -abs(v - c) / 18.0 for k, c in centers.items()}
    m = max(logits.values())
    exp = {k: np.exp(x - m) for k, x in logits.items()}
    s = sum(exp.values())
    return {k: exp[k] / s for k in exp}


def _pct(series, n):
    return float(series.iloc[-1] / series.iloc[-1 - n] - 1) * 100 if len(series) > n else 0.0


def _rolling_mean_corr(returns):
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


def _fit_regime(features):
    """Fit the HMM and return (regime_series, probs_dict, transition, on_prob_series).

    ``features`` columns must be ordered [momentum, rho, vol, dxy] (momentum is the
    risk-on signal). Falls back to ``None`` if the fit is degenerate.
    """
    z = (features - features.mean()) / features.std()
    X = z[["mom", "rho", "vol", "dxy"]].values
    if len(X) < 40 or not np.isfinite(X).all():
        return None

    hmm = GaussianHMM(n_states=3).fit(X)
    states = hmm.decode(X)
    post = hmm.predict_proba(X)

    # label states by a risk score on their (standardized) means
    sm = hmm.means  # columns [mom, rho, vol, dxy]
    risk_score = sm[:, 0] - sm[:, 1] - sm[:, 2] - sm[:, 3]
    order = list(np.argsort(-risk_score))           # highest score -> Risk-On
    state_to_label = {state: LABELS[rank] for rank, state in enumerate(order)}
    label_to_state = {v: k for k, v in state_to_label.items()}

    reg_series = pd.Series([state_to_label[s] for s in states], index=features.index)
    cur = post[-1]
    probs = {lab: float(cur[label_to_state[lab]]) for lab in LABELS}
    A = hmm.transmat
    transition = [[round(float(A[label_to_state[LABELS[i]], label_to_state[LABELS[j]]]), 2)
                   for j in range(3)] for i in range(3)]
    on_prob = pd.Series(post[:, label_to_state["Risk-On"]], index=features.index)
    return reg_series, probs, transition, on_prob


def compute(price_df, tnx=None):
    """Run the model. Returns ``(data_dict, asset_names, corr_matrix)``."""
    px = price_df
    ret = np.log(px / px.shift(1)).dropna()
    as_of = px.index[-1]

    # ---- conditional correlation ----
    window = min(CORR_WINDOW, len(ret))
    rt = ret.tail(window).corr().reindex(index=ASSET_NAMES, columns=ASSET_NAMES)
    corr = rt.values
    rho_series = _rolling_mean_corr(ret)
    rho_bar = float(rho_series.iloc[-1])

    # ---- risk basket, GARCH volatility ----
    risk_ret = ret[RISK].mean(axis=1)
    gvol = pd.Series(fit_vol(risk_ret.values), index=risk_ret.index)

    mom = risk_ret.rolling(MOM_WINDOW).sum()
    vol = risk_ret.rolling(MOM_WINDOW).std()
    dxy_chg = np.log(px["DXY"] / px["DXY"].shift(MOM_WINDOW))
    rho_aligned = rho_series.reindex(ret.index)

    # ---- composite Macro Undertow Index (continuous gauge) ----
    feat_idx = pd.DataFrame({"mom": mom, "vol": vol, "dxy": dxy_chg, "rho": rho_aligned}).dropna()
    z = (feat_idx - feat_idx.mean()) / feat_idx.std()
    score = z["mom"] - z["dxy"] - z["rho"] - z["vol"]
    index = (score.rank(pct=True) * 100.0).dropna()
    cur_index = float(index.iloc[-1])

    # ---- hidden Markov regime (Baum-Welch + Viterbi) ----
    feat_hmm = pd.DataFrame({"mom": mom, "rho": rho_aligned,
                             "vol": gvol.reindex(ret.index), "dxy": dxy_chg}).dropna()
    fitted = None
    try:
        fitted = _fit_regime(feat_hmm)
    except Exception:  # noqa: BLE001 - never let a bad fit break the pipeline
        fitted = None

    if fitted is not None:
        reg_series, cur_probs, transition, on_prob = fitted
        cur_regime = reg_series.iloc[-1]
        model_kind = "hmm"
    else:
        reg_series = index.apply(_regime_of)
        cur_regime = _regime_of(cur_index)
        cur_probs = _probs_of(cur_index)
        on_prob = (index / 100.0).clip(0, 1)
        idx_of = {l: i for i, l in enumerate(LABELS)}
        t = np.zeros((3, 3))
        seq0 = reg_series.values
        for i in range(len(seq0) - 1):
            t[idx_of[seq0[i]], idx_of[seq0[i + 1]]] += 1
        t = np.divide(t, t.sum(1, keepdims=True), out=np.zeros_like(t), where=t.sum(1, keepdims=True) != 0)
        transition = [[round(float(x), 2) for x in row] for row in t]
        model_kind = "threshold"

    reg_aligned = reg_series.reindex(index.index).ffill().bfill()

    # ---- per-asset beta to dIndex ----
    d_index = (index / 100.0).diff()
    aligned_ret = ret.reindex(index.index)
    raw = {}
    for a in ASSET_NAMES:
        x, y = d_index.values, aligned_ret[a].values
        msk = ~np.isnan(x) & ~np.isnan(y)
        raw[a] = float(np.polyfit(x[msk], y[msk], 1)[0]) if msk.sum() > 10 else 0.0
    spx_b = raw.get("SPX", 1.0) or 1.0
    betas = sorted([[a, round(b / abs(spx_b), 1)] for a, b in raw.items()], key=lambda r: -r[1])

    # ---- per-regime statistics ----
    seq = reg_aligned.values
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
        days = reg_aligned[reg_aligned == lab].index
        durs = [c for l, c in runs if l == lab]
        regime_stats[lab] = {
            "rho": round(float(rho_aligned.reindex(days).mean()) if len(days) else 0.0, 2),
            "vol": round(float(gvol.reindex(days).mean() * np.sqrt(252) * 100) if len(days) else 0.0),
            "share": round(len(days) / len(reg_aligned) * 100),
            "dur": round(float(np.mean(durs)), 1) if durs else 0,
        }

    # ---- liquidity drivers ----
    dxy_now, dxy_20 = float(px["DXY"].iloc[-1]), _pct(px["DXY"], 20)
    btc_30 = _pct(px["BTC"], 30)
    rb_vol = float(gvol.iloc[-1] * np.sqrt(252) * 100)
    drivers = [
        {"k": "Dollar index (DXY)", "v": "%.1f" % dxy_now, "tone": "bad" if dxy_20 > 0 else "good",
         "note": ("tightening" if dxy_20 > 0 else "easing") + " (%+.1f%% 20d)" % dxy_20},
        {"k": "Risk basket 20d", "v": "%+.1f%%" % (float(mom.iloc[-1]) * 100),
         "tone": "good" if mom.iloc[-1] > 0 else "bad", "note": "BTC, ETH, SPX, NDX, KOSPI"},
        {"k": "BTC 30d momentum", "v": "%+.1f%%" % btc_30, "tone": "good" if btc_30 > 0 else "bad",
         "note": "trailing 30 sessions"},
        {"k": "GARCH volatility (ann.)", "v": "%.0f%%" % rb_vol, "tone": "neu", "note": "risk basket"},
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
        "regime": [reg_aligned.loc[d] for d in index.index],
    }

    # ---- recent feed (last 6) ----
    on_aligned = on_prob.reindex(index.index).ffill().bfill()
    feed = []
    for d in list(index.index)[-6:][::-1]:
        feed.append({"date": d, "regime": reg_aligned.loc[d],
                     "index": round(float(index.loc[d])), "pon": round(float(on_aligned.loc[d]), 2)})

    # ---- 36-week regime history ----
    weekly = reg_aligned.iloc[::-5][::-1].tail(36)
    hmap = {"Risk-On": "o", "Neutral": "n", "Risk-Off": "g"}
    history = [hmap[r] for r in weekly.values]

    data = {
        "as_of": as_of,
        "window_days": int(window),
        "model": model_kind,
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
