assets = ["BTC","ETH","SPX","NDX","KOSPI","Gold","Oil","DXY"]
M = {
 ("BTC","ETH"):.82,("BTC","SPX"):.45,("BTC","NDX"):.52,("BTC","KOSPI"):.40,("BTC","Gold"):.10,("BTC","Oil"):.22,("BTC","DXY"):-.38,
 ("ETH","SPX"):.42,("ETH","NDX"):.50,("ETH","KOSPI"):.38,("ETH","Gold"):.08,("ETH","Oil"):.20,("ETH","DXY"):-.35,
 ("SPX","NDX"):.93,("SPX","KOSPI"):.62,("SPX","Gold"):.05,("SPX","Oil"):.35,("SPX","DXY"):-.30,
 ("NDX","KOSPI"):.58,("NDX","Gold"):.02,("NDX","Oil"):.30,("NDX","DXY"):-.33,
 ("KOSPI","Gold"):.12,("KOSPI","Oil"):.33,("KOSPI","DXY"):-.28,
 ("Gold","Oil"):.18,("Gold","DXY"):-.45,
 ("Oil","DXY"):-.20,
}
def corr(a,b):
    if a==b: return 1.0
    if (a,b) in M: return M[(a,b)]
    if (b,a) in M: return M[(b,a)]
    return 0.0
def lerp(c1,c2,t): return tuple(round(c1[i]+(c2[i]-c1[i])*t) for i in range(3))
def color(v):
    base=(22,22,26)
    if v>=0:
        t=v**0.85
        c=lerp(base,(224,164,92),min(t,1))
        if v>0.85: c=lerp((224,164,92),(244,212,150),(v-0.85)/0.15)
        return c
    t=min(1.0,((-v)*1.7))**0.9
    return lerp(base,(64,170,160),t)
def hexc(c): return "#%02x%02x%02x"%c
def textcol(c): return "#15161c" if sum(c)>360 else "#cfcbc2"

L=86; T=76; cs=40; n=len(assets); grid=cs*n
W=L+grid+96; H=T+grid+24
o=[]
o.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="Inter,Helvetica,Arial,sans-serif">'%(W,H))
for j,a in enumerate(assets):
    x=L+j*cs+cs/2; y=T-10
    o.append('<text x="%d" y="%d" transform="rotate(-50 %d %d)" text-anchor="start" font-size="11.5" fill="#b9b6ad">%s</text>'%(x,y,x,y,a))
for i,a in enumerate(assets):
    ry=T+i*cs+cs/2+4
    o.append('<text x="%d" y="%d" text-anchor="end" font-size="11.5" fill="#b9b6ad">%s</text>'%(L-10,ry,a))
    for j,b in enumerate(assets):
        v=corr(a,b); c=color(v); x=L+j*cs; y=T+i*cs
        o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'%(x,y,cs-2,cs-2,hexc(c)))
        txt='%.2f'%v if i!=j else '1.0'
        o.append('<text x="%d" y="%d" text-anchor="middle" font-size="9.5" fill="%s">%s</text>'%(x+(cs-2)/2,y+(cs-2)/2+4,textcol(c),txt))
cbx=L+grid+34; cbw=14; cbh=grid; cby=T
o.append('<defs><linearGradient id="cb" x1="0" y1="0" x2="0" y2="1">')
for off,v in [(0,1.0),(.25,.5),(.5,0.0),(.75,-.5),(1,-1.0)]:
    o.append('<stop offset="%s" stop-color="%s"/>'%(off,hexc(color(v))))
o.append('</linearGradient></defs>')
o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="url(#cb)" stroke="#2a2c33" stroke-width="0.6"/>'%(cbx,cby,cbw,cbh))
for off,lab in [(0,"+1"),(.5,"0"),(1,"−1")]:
    ty=cby+off*cbh+4
    o.append('<text x="%d" y="%d" font-size="10.5" fill="#8b8780">%s</text>'%(cbx+cbw+6,ty,lab))
o.append('<text x="%d" y="%d" font-size="10" fill="#8b8780">ρ</text>'%(cbx-2,cby-12))
o.append('</svg>')
open("heatmap.svg","w",encoding="utf-8").write("\n".join(o))
print("wrote heatmap.svg",W,H)
