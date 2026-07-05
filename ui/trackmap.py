"""i2-style track map: the outline is learned from the car's world path and
COLOURED BY SPEED — blue (slow) through green/yellow to red (fast), exactly
like the classic i2 speed map. A white dot marks the live position."""
from __future__ import annotations

import pyqtgraph as pg
from PyQt6 import QtWidgets

from . import theme

# blue -> cyan -> green -> yellow -> red
_STOPS = ["#2f6bff", "#00c8ff", "#00dc00", "#ffff00", "#ff3232"]


def _speed_color(frac: float) -> str:
    frac = max(0.0, min(1.0, frac))
    seg = frac * (len(_STOPS) - 1)
    i = min(int(seg), len(_STOPS) - 2)
    return theme._lerp(_STOPS[i], _STOPS[i + 1], seg - i)


class TrackMap(QtWidgets.QFrame):
    MAX_PTS = 2200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(4)
        title = QtWidgets.QLabel("TRACK MAP · цвет = скорость")
        title.setObjectName("h")
        root.addWidget(title)

        self.plot = pg.PlotWidget(background=theme.PANEL)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        self.plot.hideAxis("left")
        self.plot.hideAxis("bottom")
        self.plot.setAspectLocked(True)
        root.addWidget(self.plot)

        self.scatter = pg.ScatterPlotItem(size=4, pen=None, pxMode=True)
        self.plot.addItem(self.scatter)
        self.dot = self.plot.plot([], [], pen=None, symbol="o", symbolSize=11,
                                  symbolBrush="#ffffff",
                                  symbolPen=pg.mkPen("#000000", width=2))
        self.dot.setZValue(10)

        self._pts = []          # (x, y, speed)
        self._brushes = []
        self._last = None
        self._vmax = 1.0
        self._track = None

    def _recolor_all(self):
        self._brushes = [pg.mkBrush(_speed_color(s / self._vmax))
                         for _x, _y, s in self._pts]

    def update_frame(self, f):
        x, y = f.pos_x, f.pos_y
        if x == 0 and y == 0:
            return
        # reset the learned outline when the track changes
        if f.track and f.track != self._track:
            self._track = f.track
            self._pts, self._brushes, self._last = [], [], None
            self._vmax = 1.0
            self.scatter.setData([])

        if self._last is None or (x - self._last[0]) ** 2 + (y - self._last[1]) ** 2 > 64:
            self._last = (x, y)
            spd = max(0.0, float(f.speed))
            self._pts.append((x, y, spd))
            if len(self._pts) > self.MAX_PTS:
                self._pts.pop(0)
                self._brushes.pop(0)
            # adaptive scale: recolour everything when the max speed grows
            if spd > self._vmax * 1.08:
                self._vmax = spd
                self._recolor_all()
            else:
                self._vmax = max(self._vmax, spd)
                self._brushes.append(pg.mkBrush(_speed_color(spd / self._vmax)))
            while len(self._brushes) < len(self._pts):
                self._brushes.append(pg.mkBrush(_speed_color(1.0)))
            self.scatter.setData(
                x=[p[0] for p in self._pts],
                y=[p[1] for p in self._pts],
                brush=self._brushes)
        self.dot.setData([x], [y])
