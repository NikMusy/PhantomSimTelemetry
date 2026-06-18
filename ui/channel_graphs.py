"""The scrolling multi-channel worksheet — the heart of the display.

A dense vertical stack of time-strip charts sharing one X axis (elapsed time),
ATLAS/MoTeC style: each channel has a left gutter with its name, unit and live
value. Hover anywhere over the traces to drop a cursor and read every channel's
value at that instant; move the mouse away to return to the live edge.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtGui, QtWidgets

from . import theme

pg.setConfigOptions(antialias=True, background=theme.BG, foreground=theme.FG_DIM)


class RingBuffer:
    def __init__(self, capacity: int, nchan: int):
        self.cap = capacity
        self.n = nchan
        self.t = np.zeros(capacity, dtype=np.float64)
        self.data = np.zeros((nchan, capacity), dtype=np.float64)
        self.count = 0
        self.head = 0

    def push(self, t: float, values):
        i = self.head
        self.t[i] = t
        d = self.data
        for c in range(self.n):
            d[c, i] = values[c]
        self.head = (i + 1) % self.cap
        if self.count < self.cap:
            self.count += 1

    def view(self):
        if self.count == 0:
            return self.t[:0], self.data[:, :0]
        if self.count < self.cap:
            return self.t[:self.count], self.data[:, :self.count]
        idx = np.concatenate([np.arange(self.head, self.cap), np.arange(0, self.head)])
        return self.t[idx], self.data[:, idx]


# ---- channels stored in the ring buffer (order = buffer column) -------------
# key, extractor(frame)
CHANNELS = [
    ("speed", lambda f: f.speed),
    ("thr",   lambda f: f.throttle * 100.0),
    ("brk",   lambda f: f.brake * 100.0),
    ("steer", lambda f: f.steer),
    ("glat",  lambda f: f.g_lat),
    ("glong", lambda f: f.g_long),
    ("gear",  lambda f: float(f.gear)),
    ("rpm",   lambda f: f.rpm),
    ("delta", lambda f: f.delta_best),
]
IDX = {k: i for i, (k, _) in enumerate(CHANNELS)}

GLAT_COL = theme.RPM        # orange
GLONG_COL = theme.SPEED     # cyan

# row: (label, unit, [(chan_key, colour)], yrange or None, fmt)
ROWS = [
    ("SPEED",   "km/h", [("speed", theme.SPEED)],                       (0, 360),     "{:.0f}"),
    ("THR/BRK", "%",    [("thr", theme.THROTTLE), ("brk", theme.BRAKE)],(-3, 108),    None),
    ("STEER",   "",     [("steer", theme.STEER)],                       (-1.1, 1.1),  "{:+.2f}"),
    ("G LAT",   "g",    [("glat", GLAT_COL)],                           (-3.6, 3.6),  "{:+.2f}"),
    ("G LONG",  "g",    [("glong", GLONG_COL)],                         (-4.2, 2.6),  "{:+.2f}"),
    ("GEAR",    "",     [("gear", theme.GEAR)],                         (-1.4, 9.4),  None),
    ("ENGINE",  "rpm",  [("rpm", theme.RPM)],                           None,         "{:.0f}"),
    ("Δ BEST",  "s",    [("delta", theme.STEER)],                       (-2.0, 2.0),  "{:+.3f}"),
]


class ChannelGraphs(QtWidgets.QWidget):
    WINDOW_S = 22.0
    CAP = 2600

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buf = RingBuffer(self.CAP, len(CHANNELS))
        self._max_rpm = 9000.0
        self._smax = 360.0
        self._t = np.zeros(0)
        self._data = np.zeros((len(CHANNELS), 0))
        self._hover_t = None

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setBackground(theme.BG)
        lay.addWidget(self.glw)

        gl = self.glw.ci.layout
        gl.setColumnFixedWidth(0, 140)
        gl.setHorizontalSpacing(2)
        gl.setVerticalSpacing(2)
        gl.setContentsMargins(4, 4, 8, 4)

        self.plots, self.labels, self.curves, self.vlines = [], [], {}, []
        self._first = None
        cur_pen = pg.mkPen(theme.FG_DIM, width=1, style=pg.QtCore.Qt.PenStyle.DashLine)

        for r, (name, unit, specs, yr, _fmt) in enumerate(ROWS):
            lbl = pg.LabelItem(justify="left")
            self.glw.addItem(lbl, row=r, col=0)
            self.labels.append(lbl)

            p = self.glw.addPlot(row=r, col=1)
            p.setMenuEnabled(False)
            p.setMouseEnabled(x=False, y=False)
            p.hideButtons()
            p.showGrid(x=True, y=False, alpha=0.16)
            p.getAxis("left").setWidth(48)
            p.getAxis("left").setStyle(tickFont=_tickfont())
            p.getAxis("left").setTextPen(theme.FG_FAINT)
            p.getAxis("bottom").setTextPen(theme.FG_FAINT)
            for ax in ("left", "bottom", "top", "right"):
                p.getAxis(ax).setPen(theme.GRID)
            if yr:
                p.setYRange(*yr, padding=0)
            if r < len(ROWS) - 1:
                p.getAxis("bottom").setStyle(showValues=False)
            if self._first is None:
                self._first = p
            else:
                p.setXLink(self._first)
            # zero reference line for bipolar channels
            if yr and yr[0] < 0:
                p.addLine(y=0, pen=pg.mkPen(theme.GRID, width=1))
            for key, color in specs:
                curve = p.plot([], [], pen=pg.mkPen(color=color, width=1.7))
                self.curves[key] = (curve, IDX[key])
            vl = p.addLine(x=0, pen=cur_pen)
            vl.setVisible(False)
            self.vlines.append(vl)
            self.plots.append(p)

        self._proxy = pg.SignalProxy(self.glw.scene().sigMouseMoved,
                                     rateLimit=60, slot=self._on_mouse)
        self._live_labels(_zeros())

    # ---- data in ----------------------------------------------------
    def push(self, f):
        self._max_rpm = max(self._max_rpm, f.max_rpm or 0, f.rpm or 0)
        self.buf.push(f.t, [fn(f) for _, fn in CHANNELS])

    def redraw(self, f):
        t, data = self.buf.view()
        self._t, self._data = t, data
        if len(t) < 2:
            self._live_labels(_vals_from_frame(f))
            return
        for key, (curve, ch) in self.curves.items():
            curve.setData(t, data[ch])
        now = t[-1]
        self._first.setXRange(now - self.WINDOW_S, now, padding=0)
        self.plots[IDX_ROW["ENGINE"]].setYRange(0, self._max_rpm * 1.05, padding=0)
        self._smax = max(self._smax, float(np.max(data[IDX["speed"]])) if len(t) else 0)
        self.plots[0].setYRange(0, max(360, self._smax * 1.04), padding=0)

        if self._hover_t is not None and t[0] <= self._hover_t <= now:
            j = int(np.argmin(np.abs(t - self._hover_t)))
            for vl in self.vlines:
                vl.setVisible(True)
                vl.setValue(t[j])
            self._set_labels({k: data[IDX[k]][j] for k in IDX}, hovered=True)
        else:
            for vl in self.vlines:
                vl.setVisible(False)
            self._live_labels(_vals_from_frame(f))

    # ---- hover cursor ----------------------------------------------
    def _on_mouse(self, evt):
        try:
            pos = evt[0]
            vb = self._first.vb
            if self._first.sceneBoundingRect().contains(pos):
                self._hover_t = float(vb.mapSceneToView(pos).x())
            else:
                self._hover_t = None
        except Exception:
            self._hover_t = None

    def leaveEvent(self, e):
        self._hover_t = None
        super().leaveEvent(e)

    # ---- gutter labels ---------------------------------------------
    def _live_labels(self, vals):
        self._set_labels(vals, hovered=False)

    def _set_labels(self, v, hovered=False):
        accent = theme.GEAR if hovered else None
        for r, (name, unit, specs, yr, fmt) in enumerate(ROWS):
            if specs and specs[0][0] == "thr":
                inner = (f"<span style='color:{theme.THROTTLE};font-size:15pt;"
                         f"font-weight:700'>{v.get('thr', 0):.0f}</span>"
                         f"<span style='color:{theme.FG_FAINT};font-size:12pt'> / </span>"
                         f"<span style='color:{theme.BRAKE};font-size:15pt;"
                         f"font-weight:700'>{v.get('brk', 0):.0f}</span>")
                col = theme.FG
            else:
                key, col = specs[0]
                val = v.get(key, 0.0)
                if key == "gear":
                    txt = "R" if val < 0 else ("N" if val == 0 else str(int(round(val))))
                else:
                    txt = (fmt or "{:.0f}").format(val)
                inner = (f"<span style='color:{col};font-size:17pt;"
                         f"font-weight:700'>{txt}</span>")
            u = f" <span style='color:{theme.FG_FAINT};font-size:8pt'>{unit}</span>" if unit else ""
            nmcol = accent or theme.FG_DIM
            self.labels[r].setText(
                f"<div style='line-height:1.02'>"
                f"<span style='color:{nmcol};font-size:8.5pt;font-weight:600;"
                f"letter-spacing:1px'>{name}{u}</span><br>{inner}</div>")


IDX_ROW = {name: r for r, (name, *_rest) in enumerate(ROWS)}


def _vals_from_frame(f):
    return {k: fn(f) for k, fn in CHANNELS}


def _zeros():
    return {k: 0.0 for k, _ in CHANNELS}


def _tickfont():
    fnt = QtGui.QFont("Consolas", 7)
    return fnt
