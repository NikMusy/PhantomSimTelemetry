"""G-G meter: lateral vs longitudinal acceleration as a dot on concentric g
rings, with a short fading trail and peak readouts. A staple of MoTeC/ATLAS."""
from __future__ import annotations

from collections import deque

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme

MAX_G = 3.5


class GMeter(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setMinimumSize(220, 220)
        self.glat = 0.0
        self.glong = 0.0
        self.peak = 0.0
        self._trail = deque(maxlen=70)

    def set(self, glat, glong):
        self.glat, self.glong = glat, glong
        mag = (glat * glat + glong * glong) ** 0.5
        self.peak = max(self.peak * 0.999, mag)
        self._trail.append((glat, glong))
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # title
        p.setPen(QtGui.QColor(theme.FG_DIM))
        f = p.font(); f.setPointSize(8); f.setBold(True); p.setFont(f)
        p.drawText(QtCore.QRectF(10, 6, w - 20, 14),
                   QtCore.Qt.AlignmentFlag.AlignLeft, "G-G  •  ускорения")

        cx, cy = w / 2.0, h / 2.0 + 6
        R = min(w, h - 24) / 2.0 - 10
        scale = R / MAX_G

        # rings at 1,2,3 g
        p.setPen(QtGui.QPen(QtGui.QColor(theme.GRID), 1))
        f2 = p.font(); f2.setPointSize(7); f2.setBold(False); p.setFont(f2)
        for g in (1, 2, 3):
            rr = g * scale
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawEllipse(QtCore.QRectF(cx - rr, cy - rr, 2 * rr, 2 * rr))
            p.setPen(QtGui.QColor(theme.FG_FAINT))
            p.drawText(QtCore.QRectF(cx + 2, cy - rr - 9, 24, 10),
                       QtCore.Qt.AlignmentFlag.AlignLeft, f"{g}g")
            p.setPen(QtGui.QPen(QtGui.QColor(theme.GRID), 1))
        # crosshair
        p.drawLine(QtCore.QPointF(cx - R, cy), QtCore.QPointF(cx + R, cy))
        p.drawLine(QtCore.QPointF(cx, cy - R), QtCore.QPointF(cx, cy + R))

        # trail (oldest faint -> newest bright)
        n = len(self._trail)
        for i, (gl, go) in enumerate(self._trail):
            x = cx + gl * scale
            y = cy - go * scale
            a = int(30 + 150 * (i / max(1, n)))
            col = QtGui.QColor(theme.SPEED); col.setAlpha(a)
            p.setBrush(col); p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.drawEllipse(QtCore.QPointF(x, y), 2.4, 2.4)

        # current dot
        x = cx + self.glat * scale
        y = cy - self.glong * scale
        p.setBrush(QtGui.QColor(theme.GEAR))
        p.setPen(QtGui.QPen(QtGui.QColor("#0a0c10"), 2))
        p.drawEllipse(QtCore.QPointF(x, y), 6, 6)

        # readouts
        p.setPen(QtGui.QColor(theme.FG))
        f3 = p.font(); f3.setPointSize(9); f3.setBold(True); p.setFont(f3)
        p.drawText(QtCore.QRectF(8, h - 20, w - 16, 16),
                   QtCore.Qt.AlignmentFlag.AlignLeft,
                   f"LAT {self.glat:+.2f}   LON {self.glong:+.2f}")
        p.setPen(QtGui.QColor(theme.ACCENT))
        p.drawText(QtCore.QRectF(8, h - 20, w - 16, 16),
                   QtCore.Qt.AlignmentFlag.AlignRight, f"peak {self.peak:.2f}g")
        p.end()

    def update_frame(self, f):
        if f.connected:
            self.set(f.g_lat, f.g_long)
