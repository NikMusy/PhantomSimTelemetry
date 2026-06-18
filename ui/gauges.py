"""Right-hand gauge column: shift-light RPM bar, big gear/speed, pedal bars,
lap timing, fuel and game-specific extras (DRS/ERS for F1, boost for LMU)."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme
from sources.base import fmt_time


class RpmBar(QtWidgets.QWidget):
    """Horizontal RPM bar with a row of shift lights above it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(54)
        self.pct = 0.0
        self.rpm = 0.0

    def set(self, rpm, max_rpm):
        self.rpm = rpm
        self.pct = max(0.0, min(1.0, rpm / max_rpm)) if max_rpm > 0 else 0.0
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # shift lights row
        n = 16
        gap = 3
        lw = (w - gap * (n - 1)) / n
        lh = 12
        lit = int(self.pct * n + 0.001)
        for i in range(n):
            x = i * (lw + gap)
            frac = i / (n - 1)
            if frac < 0.6:
                col = QtGui.QColor(theme.THROTTLE)
            elif frac < 0.85:
                col = QtGui.QColor(theme.GEAR)
            else:
                col = QtGui.QColor(theme.BRAKE)
            if i >= lit:
                col = QtGui.QColor(theme.GRID)
            p.setBrush(col)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.drawRoundedRect(QtCore.QRectF(x, 0, lw, lh), 2, 2)
        # bar
        bar_y = lh + 8
        bar_h = h - bar_y - 2
        p.setBrush(QtGui.QColor(theme.PANEL_HI))
        p.setPen(QtGui.QPen(QtGui.QColor(theme.BORDER)))
        p.drawRoundedRect(QtCore.QRectF(0, bar_y, w, bar_h), 4, 4)
        grad = QtGui.QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QtGui.QColor(theme.SPEED))
        grad.setColorAt(0.65, QtGui.QColor(theme.THROTTLE))
        grad.setColorAt(0.85, QtGui.QColor(theme.GEAR))
        grad.setColorAt(1.0, QtGui.QColor(theme.BRAKE))
        p.setBrush(QtGui.QBrush(grad))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        fw = max(0.0, (w - 2) * self.pct)
        p.drawRoundedRect(QtCore.QRectF(1, bar_y + 1, fw, bar_h - 2), 3, 3)
        p.end()


class PedalBar(QtWidgets.QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.val = 0.0
        self.setMinimumWidth(22)

    def set(self, v):
        self.val = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QtGui.QColor(theme.PANEL_HI))
        p.setPen(QtGui.QPen(QtGui.QColor(theme.BORDER)))
        p.drawRoundedRect(QtCore.QRectF(0, 0, w, h), 3, 3)
        fh = (h - 2) * self.val
        p.setBrush(QtGui.QColor(self.color))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawRoundedRect(QtCore.QRectF(1, h - 1 - fh, w - 2, fh), 2, 2)
        p.end()


def _val(big_color="#e6edf6", size=15):
    lab = QtWidgets.QLabel("—")
    lab.setStyleSheet(f"color:{big_color};font-size:{size}px;font-weight:700;")
    return lab


def _cap(text):
    lab = QtWidgets.QLabel(text)
    lab.setStyleSheet(f"color:{theme.FG_DIM};font-size:9px;font-weight:600;"
                      "letter-spacing:1px;")
    return lab


class GaugePanel(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # RPM bar
        self.rpm_bar = RpmBar()
        root.addWidget(self.rpm_bar)

        # big gear + speed + pedals
        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(12)
        self.gear = QtWidgets.QLabel("N")
        self.gear.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.gear.setStyleSheet(f"color:{theme.GEAR};font-size:96px;font-weight:800;")
        self.gear.setMinimumWidth(120)
        mid.addWidget(self.gear)

        spd_box = QtWidgets.QVBoxLayout()
        spd_box.setSpacing(0)
        self.speed = QtWidgets.QLabel("0")
        self.speed.setStyleSheet(f"color:{theme.FG};font-size:54px;font-weight:800;")
        self.speed.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight |
                                QtCore.Qt.AlignmentFlag.AlignBottom)
        u = QtWidgets.QLabel("km/h")
        u.setStyleSheet(f"color:{theme.FG_DIM};font-size:12px;font-weight:600;")
        u.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        spd_box.addStretch(1)
        spd_box.addWidget(self.speed)
        spd_box.addWidget(u)
        mid.addLayout(spd_box, 1)

        pedals = QtWidgets.QHBoxLayout()
        pedals.setSpacing(4)
        self.brk = PedalBar(theme.BRAKE)
        self.thr = PedalBar(theme.THROTTLE)
        pedals.addWidget(self.brk)
        pedals.addWidget(self.thr)
        mid.addLayout(pedals)
        root.addLayout(mid)

        root.addWidget(_hline())

        # timing grid
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        self.v = {}
        cells = [
            ("POS", "pos"), ("LAP", "lap"),
            ("CURRENT", "cur"), ("LAST", "last"),
            ("BEST", "best"), ("DELTA", "delta"),
        ]
        for i, (cap, key) in enumerate(cells):
            r, c = divmod(i, 2)
            box = QtWidgets.QVBoxLayout()
            box.setSpacing(0)
            box.addWidget(_cap(cap))
            big = _val(size=20 if key in ("pos", "lap") else 17)
            self.v[key] = big
            box.addWidget(big)
            grid.addLayout(box, r, c)
        root.addLayout(grid)

        root.addWidget(_hline())

        # fuel + extras
        bottom = QtWidgets.QGridLayout()
        bottom.setHorizontalSpacing(10)
        bottom.setVerticalSpacing(6)
        extra = [("FUEL", "fuel"), ("WATER", "water"),
                 ("DRS / ERS", "drs"), ("BOOST", "boost")]
        for i, (cap, key) in enumerate(extra):
            r, c = divmod(i, 2)
            box = QtWidgets.QVBoxLayout()
            box.setSpacing(0)
            box.addWidget(_cap(cap))
            big = _val(size=16)
            self.v[key] = big
            box.addWidget(big)
            bottom.addLayout(box, r, c)
        root.addLayout(bottom)
        root.addStretch(1)

    # ----------------------------------------------------------------
    def update_frame(self, f):
        self.rpm_bar.set(f.rpm, f.max_rpm)
        self.gear.setText("R" if f.gear < 0 else ("N" if f.gear == 0 else str(f.gear)))
        self.speed.setText(f"{f.speed:.0f}")
        self.thr.set(f.throttle)
        self.brk.set(f.brake)

        self.v["pos"].setText(f"P{f.position}" if f.position else "—")
        self.v["lap"].setText(f"{f.lap}/{f.total_laps}" if f.total_laps else f"{f.lap}")
        self.v["cur"].setText(fmt_time(f.cur_lap_time))
        self.v["last"].setText(fmt_time(f.last_lap))
        self.v["best"].setText(fmt_time(f.best_lap))

        if f.last_lap and f.best_lap:
            d = f.last_lap - f.best_lap
            col = theme.DELTA_NEG if d <= 0 else theme.DELTA_POS
            self.v["delta"].setText(f"{d:+.3f}")
            self.v["delta"].setStyleSheet(f"color:{col};font-size:17px;font-weight:700;")
        else:
            self.v["delta"].setText("—")

        cap = f.fuel_capacity or 1
        self.v["fuel"].setText(f"{f.fuel:.1f} L")
        wc = theme.BRAKE if f.water_temp > 110 else theme.FG
        self.v["water"].setText(f"{f.water_temp:.0f}°C" if f.water_temp else "—")
        self.v["water"].setStyleSheet(f"color:{wc};font-size:16px;font-weight:700;")

        if f.game == "F1 25":
            drs = "OPEN" if f.drs else "—"
            self.v["drs"].setText(f"{drs}  {f.ers_pct:.0f}%")
            self.v["boost"].setText("—")
        else:
            self.v["drs"].setText("OPEN" if f.drs else "—")
            self.v["boost"].setText(f"{f.turbo:.2f} bar" if f.turbo else "—")


def _hline():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    line.setStyleSheet(f"color:{theme.BORDER};background:{theme.BORDER};max-height:1px;")
    return line
