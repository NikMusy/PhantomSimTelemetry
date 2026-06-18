"""Track map: records the player's world path into an outline and shows the
car's live position on it. The outline is learned on the first lap."""
from __future__ import annotations

import pyqtgraph as pg
from PyQt6 import QtWidgets

from . import theme


class TrackMap(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(4)
        title = QtWidgets.QLabel("TRACK MAP")
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

        self.path = self.plot.plot([], [], pen=pg.mkPen(theme.GRID, width=6))
        self.dot = self.plot.plot([], [], pen=None, symbol="o", symbolSize=12,
                                  symbolBrush=theme.SPEED, symbolPen=pg.mkPen("#0a0c10", width=2))

        self._xs = []
        self._ys = []
        self._last = None
        self._ranged = False
        self._track = None

    def update_frame(self, f):
        x, y = f.pos_x, f.pos_y
        if x == 0 and y == 0:
            return
        # reset the learned outline when the track changes
        if f.track and f.track != self._track:
            self._track = f.track
            self._xs, self._ys, self._last, self._ranged = [], [], None, False

        if self._last is None or (x - self._last[0]) ** 2 + (y - self._last[1]) ** 2 > 64:
            self._xs.append(x)
            self._ys.append(y)
            self._last = (x, y)
            if len(self._xs) > 2000:
                self._xs.pop(0)
                self._ys.pop(0)
            self.path.setData(self._xs, self._ys)
            if not self._ranged and len(self._xs) > 30:
                self.plot.enableAutoRange()
        self.dot.setData([x], [y])
