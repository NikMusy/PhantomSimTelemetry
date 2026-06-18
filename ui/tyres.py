"""Four-corner tyre panel: core temperature (colour-coded), pressure, life and
brake temperature for FL/FR/RL/RR."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme


class TyreCorner(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.temp = 0.0
        self.press = 0.0
        self.life = 100.0
        self.brake = 0.0
        self.setMinimumSize(120, 92)

    def set(self, temp, press, life, brake):
        self.temp, self.press, self.life, self.brake = temp, press, life, brake
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        m = 6
        tw = w * 0.46
        # tyre block, coloured by temp
        col = QtGui.QColor(theme.tyre_color(self.temp))
        rect = QtCore.QRectF(m, m, tw, h - 2 * m)
        p.setBrush(col)
        p.setPen(QtGui.QPen(QtGui.QColor(theme.BORDER)))
        p.drawRoundedRect(rect, 6, 6)
        # temp text on tyre
        p.setPen(QtGui.QColor("#0a0c10"))
        f = p.font(); f.setPointSize(13); f.setBold(True); p.setFont(f)
        p.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, f"{self.temp:.0f}°")
        # life bar inside tyre (bottom strip)
        lh = 6
        p.setBrush(QtGui.QColor(0, 0, 0, 90))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawRect(QtCore.QRectF(rect.left(), rect.bottom() - lh - 2,
                                 rect.width(), lh))
        p.setBrush(QtGui.QColor(theme.life_color(self.life)))
        p.drawRect(QtCore.QRectF(rect.left(), rect.bottom() - lh - 2,
                                 rect.width() * self.life / 100.0, lh))

        # text column (pressure / life / brake)
        tx = m + tw + 8
        p.setPen(QtGui.QColor(theme.FG))
        f2 = p.font(); f2.setPointSize(11); f2.setBold(True); p.setFont(f2)
        p.drawText(QtCore.QRectF(tx, m, w - tx - 2, 22),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   f"{self.press:.1f}")
        p.setPen(QtGui.QColor(theme.FG_DIM))
        f3 = p.font(); f3.setPointSize(8); f3.setBold(False); p.setFont(f3)
        p.drawText(QtCore.QRectF(tx, m + 20, w - tx - 2, 14),
                   QtCore.Qt.AlignmentFlag.AlignLeft, "psi")
        p.setPen(QtGui.QColor(theme.life_color(self.life)))
        f2.setPointSize(11); p.setFont(f2)
        p.drawText(QtCore.QRectF(tx, m + 36, w - tx - 2, 20),
                   QtCore.Qt.AlignmentFlag.AlignLeft, f"{self.life:.0f}%")
        p.setPen(QtGui.QColor(theme.FG_DIM))
        p.setFont(f3)
        p.drawText(QtCore.QRectF(tx, h - 22, w - tx - 2, 18),
                   QtCore.Qt.AlignmentFlag.AlignLeft,
                   f"brk {self.brake:.0f}°")
        p.end()


class TyrePanel(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(6)
        title = QtWidgets.QLabel("TYRES")
        title.setObjectName("h")
        root.addWidget(title)
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)
        self.corners = [TyreCorner() for _ in range(4)]   # FL FR RL RR
        grid.addWidget(self.corners[0], 0, 0)
        grid.addWidget(self.corners[1], 0, 1)
        grid.addWidget(self.corners[2], 1, 0)
        grid.addWidget(self.corners[3], 1, 1)
        root.addLayout(grid)

    def update_frame(self, f):
        for i in range(4):
            self.corners[i].set(f.tyre_temp[i], f.tyre_press[i],
                                f.tyre_life[i], f.brake_temp[i])
