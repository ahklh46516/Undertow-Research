# Undertow P0 engine: fetch real cross-asset data, compute regime/index, write data.json + heatmap.svg
import urllib.request, urllib.parse, json, datetime
import numpy as np, pandas as pd

ASSETS = [
    ("BTC","BTC-USD"), ("ETH","ETH-USD"), ("SPX","^GSPC"), ("Nasdaq","^IXIC"),
    ("KOSPI","^KS11"), ("Gold","GC=F"), ("Oil","CL=F"), ("DXY","DX-Y.NYB"),
]
RISK = ["BTC","ETH","SPX","Nasdaq","KOSPI"]
HDR = {"User-Agent":"Mozilla/5.0"}

def fetch(sym, tries=3):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1y&interval=1d" % urllib.parse.quote(sym)
    last=None
    for k in range(tries):
        try:
            j = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=25).read())
            res = j["chart"]["result"][0]
            break
        except Exception as e:
            last=e; import time as _t; _t.sleep(1.5)
    else:
        raise last
    ts = res["timestamp"]
    cl = res["indicators"]["quote"][0]["close"]
    out = {}
    for t,c in zip(ts,cl):
        if c is None: continue
        d = datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
        out[d] = c
    return pd.Series(out)

# also 10y yield for a driver
print("fetching ...")
prices = {}
for name,sym in ASSETS:
    prices[name] = fetch(sym); print("  ", name, len(prices[name]))
try:
    tnx = fetch("^TNX")   # 10y treasury yield (x10)
except Exception:
    tnx = None

px = pd.DataFrame(prices).sort_index()
px = px.dropna()                       # common trading days
ret = np.log(px / px.shift(1)).dropna()
asset_names = [a for a,_ in ASSETS]
as_of = px.index[-1]

# ---- correlation (trailing 90d) ----
W = min(90, len(ret))
Rt = ret.tail(W).corr()
corr = Rt.reindex(index=asset_names, columns=asset_names).values

# mean pairwise correlation, rolling 60d series (manual)
_vals = ret[asset_names].values
_dates = list(ret.index)
_win = min(60, len(ret))
_rl=[]; _rd=[]
for i in range(_win, len(ret)+1):
    c = np.corrcoef(_vals[i-_win:i], rowvar=False)
    iu = np.triu_indices(c.shape[0], 1)
    _rl.append(float(np.nanmean(c[iu]))); _rd.append(_dates[i-1])
rho_series = pd.Series(_rl, index=_rd)
rho_bar = float(rho_series.iloc[-1])

# ---- composite Undertow Index ----
risk_ret = ret[RISK].mean(axis=1)
mom = risk_ret.rolling(20).sum()
vol = risk_ret.rolling(20).std()
dxy_chg = np.log(px["DXY"]/px["DXY"].shift(20))      # dollar up = risk-off
rho_aligned = rho_series.reindex(ret.index)
df = pd.DataFrame({"mom":mom, "vol":vol, "dxy":dxy_chg, "rho":rho_aligned}).dropna()
z = (df - df.mean()) / df.std()
score = z["mom"] - z["dxy"] - z["rho"] - z["vol"]
index = score.rank(pct=True) * 100.0                  # 0..100
index = index.dropna()

def regime_of(v):
    return "Risk-On" if v>=60 else ("Neutral" if v>=40 else "Risk-Off")
reg_series = index.apply(regime_of)

def probs_of(v):
    centers = {"Risk-On":78,"Neutral":50,"Risk-Off":22}
    d = {k: -abs(v-c)/18.0 for k,c in centers.items()}
    m = max(d.values()); e={k:np.exp(x-m) for k,x in d.items()}; s=sum(e.values())
    return {k: e[k]/s for k in e}

cur_index = float(index.iloc[-1])
cur_regime = regime_of(cur_index)
cur_probs = probs_of(cur_index)

# ---- per-asset beta to dIndex ----
dI = (index/100.0).diff()
betas=[]
ar = ret.reindex(index.index)
for a in asset_names:
    x = dI.values; y = ar[a].values
    msk = ~np.isnan(x) & ~np.isnan(y)
    b = np.polyfit(x[msk], y[msk], 1)[0] if msk.sum()>10 else 0.0
    betas.append([a, round(float(b),2)])
# normalize betas to a readable scale (relative to SPX≈1)
spx_b = dict(betas).get("SPX",1.0) or 1.0
betas = [[a, round(b/abs(spx_b),1)] for a,b in betas]
betas.sort(key=lambda r:-r[1])

# ---- transition matrix from regime sequence ----
labs=["Risk-On","Neutral","Risk-Off"]; idx={l:i for i,l in enumerate(labs)}
T=np.zeros((3,3)); seq=reg_series.values
for i in range(len(seq)-1):
    T[idx[seq[i]], idx[seq[i+1]]] += 1
T = np.divide(T, T.sum(1,keepdims=True), out=np.zeros_like(T), where=T.sum(1,keepdims=True)!=0)
transition = [[round(float(x),2) for x in row] for row in T]

# ---- per-regime statistics (real) ----
runs=[]; prev=None; cnt=0
for r in reg_series.values:
    if r==prev: cnt+=1
    else:
        if prev is not None: runs.append((prev,cnt))
        prev=r; cnt=1
if prev is not None: runs.append((prev,cnt))
regime_stats={}
for lab in labs:
    idxs = reg_series[reg_series==lab].index
    rho_m = float(rho_aligned.reindex(idxs).mean()) if len(idxs) else 0.0
    vol_m = float(risk_ret.reindex(idxs).std()*np.sqrt(252)*100) if len(idxs)>1 else 0.0
    durs = [c for l,c in runs if l==lab]
    regime_stats[lab] = {"rho":round(rho_m,2), "vol":round(vol_m), "share":round(len(idxs)/len(reg_series)*100),
                         "dur":round(float(np.mean(durs)),1) if durs else 0}

# ---- drivers (real) ----
def pct(series,n):
    return float(series.iloc[-1]/series.iloc[-1-n]-1)*100 if len(series)>n else 0.0
dxy_now = float(px["DXY"].iloc[-1]); dxy_20 = pct(px["DXY"],20)
btc_30 = pct(px["BTC"],30)
rb_vol = float(vol.iloc[-1]*np.sqrt(252)*100)
drivers = [
    {"k":"Dollar index (DXY)","v":"%.1f"%dxy_now, "tone":"bad" if dxy_20>0 else "good",
     "note":("tightening" if dxy_20>0 else "easing")+" (%+.1f%% 20d)"%dxy_20},
    {"k":"Risk basket 20d","v":"%+.1f%%"%(float(mom.iloc[-1])*100), "tone":"good" if mom.iloc[-1]>0 else "bad",
     "note":"BTC, ETH, SPX, NDX, KOSPI"},
    {"k":"BTC 30d momentum","v":"%+.1f%%"%btc_30, "tone":"good" if btc_30>0 else "bad","note":"trailing 30 sessions"},
    {"k":"Realized vol (ann.)","v":"%.0f%%"%rb_vol, "tone":"neu","note":"risk basket"},
    {"k":"Mean pairwise correlation","v":"%.2f"%rho_bar, "tone":"bad" if rho_bar>0.4 else "good","note":"elevated" if rho_bar>0.4 else "calm / dispersed"},
]
if tnx is not None:
    y_now=float(tnx.iloc[-1]); y_20=(float(tnx.iloc[-1])-float(tnx.iloc[-21])) if len(tnx)>21 else 0
    drivers.insert(1,{"k":"10y Treasury yield","v":"%.2f%%"%y_now,"tone":"bad" if y_20>0 else "good",
        "note":("rising" if y_20>0 else "falling")+" (%+.2f 20d)"%y_20})

# ---- time series for chart (downsample) ----
ser_idx = index
ser_rho = (rho_aligned.reindex(ser_idx.index)).clip(0,1)*100
dates = list(ser_idx.index)
chart = {
    "dates": dates,
    "index": [round(float(v),1) for v in ser_idx.values],
    "rho":   [round(float(v),1) for v in ser_rho.values],
    "regime":[regime_of(v) for v in ser_idx.values],
}

# ---- recent feed (last 6) ----
feed=[]
for d in list(index.index)[-6:][::-1]:
    v=float(index.loc[d]); p=probs_of(v)
    feed.append({"date":d,"regime":regime_of(v),"index":round(v),"pon":round(p["Risk-On"],2)})

# ---- 36-week regime history ----
weekly = reg_series.iloc[::-5][::-1].tail(36)
hmap={"Risk-On":"o","Neutral":"n","Risk-Off":"g"}
history=[hmap[r] for r in weekly.values]

data = {
    "as_of": as_of, "window_days": int(W),
    "index": round(cur_index), "index_exact": round(cur_index,1),
    "regime": cur_regime,
    "probs": {"on":round(cur_probs["Risk-On"],2),"neutral":round(cur_probs["Neutral"],2),"off":round(cur_probs["Risk-Off"],2)},
    "rho_bar": round(rho_bar,2),
    "drivers": drivers, "betas": betas,
    "assets": asset_names, "corr": [[round(float(x),2) for x in row] for row in corr],
    "transition": transition, "history": history, "feed": feed, "chart": chart,
    "regime_stats": regime_stats,
    "prices": {a: round(float(px[a].iloc[-1]),2) for a in asset_names},
}
json.dump(data, open("data.json","w"), indent=1)
print("wrote data.json  as_of=%s  index=%s  regime=%s  rho=%.2f"%(as_of,data["index"],cur_regime,rho_bar))

# ---- regenerate heatmap.svg from REAL corr ----
def lerp(c1,c2,t): return tuple(round(c1[i]+(c2[i]-c1[i])*t) for i in range(3))
def color(v):
    base=(22,22,26)
    if v>=0:
        t=v**0.85; c=lerp(base,(224,164,92),min(t,1))
        if v>0.85: c=lerp((224,164,92),(244,212,150),(v-0.85)/0.15)
        return c
    return lerp(base,(64,170,160),min(1.0,((-v)*1.7))**0.9)
def hexc(c): return "#%02x%02x%02x"%c
def tc(c): return "#15161c" if sum(c)>360 else "#cfcbc2"
L=86;Tt=76;cs=40;n=len(asset_names);grid=cs*n;W2=L+grid+96;H2=Tt+grid+24
o=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="Inter,Helvetica,Arial,sans-serif">'%(W2,H2)]
for j,a in enumerate(asset_names):
    x=L+j*cs+cs/2;y=Tt-10
    o.append('<text x="%d" y="%d" transform="rotate(-50 %d %d)" font-size="11" fill="#b9b6ad">%s</text>'%(x,y,x,y,a))
for i,a in enumerate(asset_names):
    ry=Tt+i*cs+cs/2+4
    o.append('<text x="%d" y="%d" text-anchor="end" font-size="11" fill="#b9b6ad">%s</text>'%(L-10,ry,a))
    for j2 in range(n):
        v=corr[i][j2];c=color(v);x=L+j2*cs;y=Tt+i*cs
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'%(x,y,cs-2,cs-2,hexc(c)))
        o.append('<text x="%d" y="%d" text-anchor="middle" font-size="9.5" fill="%s">%s</text>'%(x+(cs-2)/2,y+(cs-2)/2+4,tc(c),('%.2f'%v if i!=j2 else '1.0')))
cbx=L+grid+34;cbw=14;cbh=grid
o.append('<defs><linearGradient id="cb" x1="0" y1="0" x2="0" y2="1">')
for off,v in [(0,1.0),(.5,0.0),(1,-1.0)]: o.append('<stop offset="%s" stop-color="%s"/>'%(off,hexc(color(v))))
o.append('</linearGradient></defs>')
o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="url(#cb)" stroke="#2a2c33" stroke-width="0.6"/>'%(cbx,Tt,cbw,cbh))
for off,lab in [(0,"+1"),(.5,"0"),(1,"−1")]:
    o.append('<text x="%d" y="%d" font-size="10.5" fill="#8b8780">%s</text>'%(cbx+cbw+6,Tt+off*cbh+4,lab))
o.append('</svg>')
open("heatmap.svg","w",encoding="utf-8").write("\n".join(o))
print("wrote heatmap.svg from real correlations")
