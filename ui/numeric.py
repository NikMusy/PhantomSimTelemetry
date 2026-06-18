"""Dense numeric channel report — an ATLAS/MoTeC-style grid of live values for
all the secondary channels that don't get their own trace or gauge."""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from . import theme


def _on(x):
    return ("ON", theme.THROTTLE) if x else ("—", theme.FG_FAINT)


# (caption, value-fn -> (text, color))
CELLS = [
    ("WATER",  lambda f: (f"{f.water_temp:.0f}°", theme.BRAKE if f.water_temp > 110 else theme.FG)),
    ("OIL T",  lambda f: (f"{f.oil_temp:.0f}°", theme.BRAKE if f.oil_temp > 140 else theme.FG)),
    ("OIL P",  lambda f: (f"{f.oil_press:.1f}", theme.FG)),
    ("FUEL P", lambda f: (f"{f.fuel_press:.1f}", theme.FG)),
    ("MANIF",  lambda f: (f"{f.manifold_press:.2f}", theme.FG)),
    ("VOLTS",  lambda f: (f"{f.voltage:.1f}", theme.BRAKE if 0 < f.voltage < 12 else theme.FG)),

    ("FUEL",   lambda f: (f"{f.fuel:.1f}L", theme.FG)),
    ("FUEL %", lambda f: (f"{f.fuel_pct * 100:.0f}%", theme.GEAR if f.fuel_pct < 0.1 else theme.FG)),
    ("FUEL/H", lambda f: (f"{f.fuel_per_hour:.1f}", theme.FG)),
    ("B.BIAS", lambda f: (f"{f.brake_bias:.1f}%", theme.FG)),
    ("ABS",    lambda f: _on(f.abs_active)),
    ("TC",     lambda f: (("ON", theme.THROTTLE) if f.tc_active else (f"{f.tc_level:.0f}", theme.FG))),

    ("YAW",    lambda f: (f"{f.yaw_rate:+.0f}", theme.FG)),
    ("PITCH",  lambda f: (f"{f.pitch:+.1f}", theme.FG)),
    ("ROLL",   lambda f: (f"{f.roll:+.1f}", theme.FG)),
    ("STR Nm", lambda f: (f"{f.steer_torque:+.1f}", theme.FG)),
    ("TRACK",  lambda f: (f"{f.track_temp:.0f}°", theme.FG)),
    ("AIR",    lambda f: (f"{f.air_temp:.0f}°", theme.FG)),

    ("WIND",   lambda f: (f"{f.wind_vel:.1f}", theme.FG)),
    ("INCID",  lambda f: (f"{f.incidents}x", theme.BRAKE if f.incidents else theme.FG)),
    ("Δ BEST", lambda f: (f"{f.delta_best:+.2f}",
                          theme.DELTA_NEG if f.delta_best <= 0 else theme.DELTA_POS)),
    ("SECTOR", lambda f: (f"S{f.sector + 1}", theme.FG)),
    ("POS",    lambda f: (f"P{f.position}" if f.position else "—", theme.FG)),
    ("CARS",   lambda f: (f"{f.num_cars}" if f.num_cars else "—", theme.FG)),
]

COLS = 3


class NumericReport(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)
        title = QtWidgets.QLabel("DATA")
        title.setObjectName("h")
        root.addWidget(title)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(9)
        self._cells = []
        for i, (cap, _fn) in enumerate(CELLS):
            r, c = divmod(i, COLS)
            cell = QtWidgets.QVBoxLayout()
            cell.setSpacing(1)
            capw = QtWidgets.QLabel(cap)
            capw.setStyleSheet(f"color:{theme.FG_DIM};font-size:12px;font-weight:600;"
                               "letter-spacing:1px;")
            valw = QtWidgets.QLabel("—")
            valw.setStyleSheet(f"color:{theme.FG};font-size:23px;font-weight:800;")
            cell.addWidget(capw)
            cell.addWidget(valw)
            holder = QtWidgets.QWidget()
            holder.setLayout(cell)
            grid.addWidget(holder, r, c)
            self._cells.append(valw)
        root.addLayout(grid)
        root.addStretch(1)

    def update_frame(self, f):
        live = f.connected
        for valw, (_cap, fn) in zip(self._cells, CELLS):
            if not live:
                valw.setText("—")
                valw.setStyleSheet(f"color:{theme.FG_FAINT};font-size:23px;font-weight:800;")
                continue
            try:
                txt, col = fn(f)
            except Exception:
                txt, col = "—", theme.FG
            valw.setText(str(txt))
            valw.setStyleSheet(f"color:{col};font-size:23px;font-weight:800;")
