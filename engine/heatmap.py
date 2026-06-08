"""Render the conditional-correlation matrix to a standalone SVG heatmap.

A diverging colour scale: warm (gold) for strong positive co-movement, cool (teal)
for hedges / negative correlation, near-black for zero.
"""

_BASE = (22, 22, 26)
_GOLD = (224, 164, 92)
_GOLD_HI = (244, 212, 150)
_TEAL = (64, 170, 160)


def _lerp(c1, c2, t):
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _color(v):
    if v >= 0:
        c = _lerp(_BASE, _GOLD, min(v ** 0.85, 1))
        if v > 0.85:
            c = _lerp(_GOLD, _GOLD_HI, (v - 0.85) / 0.15)
        return c
    return _lerp(_BASE, _TEAL, min(1.0, ((-v) * 1.7)) ** 0.9)


def _hexc(c):
    return "#%02x%02x%02x" % c


def _text_color(c):
    return "#15161c" if sum(c) > 360 else "#cfcbc2"


def render(asset_names, corr, cell=40):
    """Return an SVG string for the ``corr`` matrix over ``asset_names``."""
    n = len(asset_names)
    left, top = 86, 76
    grid = cell * n
    width, height = left + grid + 96, top + grid + 24
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
         'font-family="Inter,Helvetica,Arial,sans-serif">' % (width, height)]

    # column headers (rotated)
    for j, a in enumerate(asset_names):
        x = left + j * cell + cell / 2
        y = top - 10
        o.append('<text x="%d" y="%d" transform="rotate(-50 %d %d)" font-size="11" fill="#b9b6ad">%s</text>'
                 % (x, y, x, y, a))

    # rows + cells
    for i, a in enumerate(asset_names):
        ry = top + i * cell + cell / 2 + 4
        o.append('<text x="%d" y="%d" text-anchor="end" font-size="11" fill="#b9b6ad">%s</text>' % (left - 10, ry, a))
        for j in range(n):
            v = corr[i][j]
            c = _color(v)
            x, y = left + j * cell, top + i * cell
            o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'
                     % (x, y, cell - 2, cell - 2, _hexc(c)))
            label = "%.2f" % v if i != j else "1.0"
            o.append('<text x="%d" y="%d" text-anchor="middle" font-size="9.5" fill="%s">%s</text>'
                     % (x + (cell - 2) / 2, y + (cell - 2) / 2 + 4, _text_color(c), label))

    # colour bar
    cbx, cbw, cbh = left + grid + 34, 14, grid
    o.append('<defs><linearGradient id="cb" x1="0" y1="0" x2="0" y2="1">')
    for off, v in [(0, 1.0), (0.5, 0.0), (1, -1.0)]:
        o.append('<stop offset="%s" stop-color="%s"/>' % (off, _hexc(_color(v))))
    o.append('</linearGradient></defs>')
    o.append('<rect x="%d" y="%d" width="%d" height="%d" rx="3" fill="url(#cb)" stroke="#2a2c33" stroke-width="0.6"/>'
             % (cbx, top, cbw, cbh))
    for off, lab in [(0, "+1"), (0.5, "0"), (1, "−1")]:
        o.append('<text x="%d" y="%d" font-size="10.5" fill="#8b8780">%s</text>' % (cbx + cbw + 6, top + off * cbh + 4, lab))
    o.append('</svg>')
    return "\n".join(o)
