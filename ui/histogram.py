"""i2-style histogram worksheet: how the session's time is distributed over
throttle position, brake pressure, speed and gear. Black plot area, bars in
the channel's trace colour, Y axis in percent of samples. Accumulates for the
whole session; resets when the track changes."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets

from . import theme

# (name, unit, colour, lo, hi, nbins, extractor)
CHANS = [
    ("THROTTLE", "%",    theme.THROTTLE, 0.0,  100.0, 25, lambda f: f.throttle * 100.0),
    ("BRAKE",    "%",    theme.BRAKE,    0.0,  100.0, 25, lambda f: f.brake * 100.0),
    ("SPEED",    "km/h", theme.SPEED,    0.0,  360.0, 36, lambda f: f.speed),
    ("GEAR",     "",     theme.GEAR,    -1.5,  9.5,   11, lambda f: float(f.gear)),
]


class HistogramSheet(QtWidgets.QWidget):
    REDRAW_EVERY = 30           # ticks (~1 s)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._track = ""
        self._total = 0
        self._tick = 0
        self._counts = [np.zeros(c[5], dtype=np.int64) for c in CHANS]
        self._bars = [None] * len(CHANS)

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        frame = QtWidgets.QFrame()
        frame.setObjectName("panel")
        fl = QtWidgets.QVBoxLayout(frame)
        fl.setContentsMargins(2, 2, 2, 2)
        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setBackground(theme.BG)
        fl.addWidget(self.glw)
        root.addWidget(frame)

        gl = self.glw.ci.layout
        gl.setColumnFixedWidth(0, 128)
        gl.setHorizontalSpacing(2)
        gl.setVerticalSpacing(2)
        gl.setContentsMargins(4, 4, 8, 4)

        self.plots, self.labels = [], []
        for r, (name, unit, col, lo, hi, nbins, _fn) in enumerate(CHANS):
            lbl = pg.LabelItem(justify="left")
            self.glw.addItem(lbl, row=r, col=0)
            self.labels.append(lbl)

            p = self.glw.addPlot(row=r, col=1)
            p.setMenuEnabled(False)
            p.setMouseEnabled(x=False, y=False)
            p.hideButtons()
            p.showGrid(x=True, y=True, alpha=0.25)
            p.getAxis("left").setWidth(48)
            p.getAxis("left").setTextPen(theme.FG_FAINT)
            p.getAxis("bottom").setTextPen(theme.FG_FAINT)
            for ax in ("left", "bottom", "top", "right"):
                p.getAxis(ax).setPen(theme.GRID)
            p.setXRange(lo, hi, padding=0.01)
            p.setYRange(0, 40, padding=0)
            if name == "GEAR":
                ticks = [(i, "R" if i == -1 else ("N" if i == 0 else str(i)))
                         for i in range(-1, 10)]
                p.getAxis("bottom").setTicks([ticks])
            self.plots.append(p)
        self._set_labels()

    # ------------------------------------------------------------------
    def _reset(self):
        for c in self._counts:
            c[:] = 0
        self._total = 0

    def update_frame(self, f):
        self._tick += 1
        if f.connected:
            if f.track and f.track != self._track:
                self._track = f.track
                self._reset()
            for i, (_n, _u, _c, lo, hi, nbins, fn) in enumerate(CHANS):
                v = fn(f)
                b = int((v - lo) / (hi - lo) * nbins)
                if 0 <= b < nbins:
                    self._counts[i][b] += 1
                elif b >= nbins:
                    self._counts[i][nbins - 1] += 1
            self._total += 1

        if not self.isVisible() or self._tick % self.REDRAW_EVERY:
            return
        self._redraw()

    def _redraw(self):
        if self._total < 10:
            return
        for i, (name, unit, col, lo, hi, nbins, _fn) in enumerate(CHANS):
            h = self._counts[i] / self._total * 100.0
            binw = (hi - lo) / nbins
            centers = lo + (np.arange(nbins) + 0.5) * binw
            if self._bars[i] is not None:
                self.plots[i].removeItem(self._bars[i])
            bar = pg.BarGraphItem(x=centers, height=h, width=binw * 0.85,
                                  brush=col, pen=pg.mkPen("#000000"))
            self.plots[i].addItem(bar)
            self._bars[i] = bar
            self.plots[i].setYRange(0, max(10.0, float(h.max()) * 1.15), padding=0)
        self._set_labels()

    def _set_labels(self):
        for i, (name, unit, col, lo, hi, nbins, _fn) in enumerate(CHANS):
            if self._total:
                # weighted mean of the distribution
                binw = (hi - lo) / nbins
                centers = lo + (np.arange(nbins) + 0.5) * binw
                cnt = self._counts[i]
                mean = float((centers * cnt).sum() / max(1, cnt.sum()))
                val = f"{mean:.0f}"
            else:
                val = "—"
            u = (f" <span style='color:{theme.FG_FAINT};font-size:8pt'>{unit}</span>"
                 if unit else "")
            self.labels[i].setText(
                f"<div style='line-height:1.02'>"
                f"<span style='color:{col};font-size:8.5pt;font-weight:700;"
                f"letter-spacing:1px'>{name}{u}</span><br>"
                f"<span style='color:{theme.FG_DIM};font-size:9pt'>сред. </span>"
                f"<span style='color:{col};font-size:14pt;font-weight:700'>{val}</span>"
                "</div>")

    def showEvent(self, e):
        self._tick = self.REDRAW_EVERY - 1   # redraw on next tick
        super().showEvent(e)
