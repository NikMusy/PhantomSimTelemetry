"""i2-style lap comparison worksheet.

Left: the list of completed laps (tick to overlay, best lap marked ★).
Right: five distance-aligned strips — Δ time vs reference ("variance"),
speed, throttle, brake and steering — with every ticked lap overlaid, the
best lap as the white reference and the lap being driven *right now* drawn
live in cyan. Hover over the traces to drop a cursor and read the
reference/live values at that point of the track.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets

from . import theme
from sources.base import fmt_time

REF_COL = "#ffffff"
LIVE_COL = "#00ffff"
# bright variants for traces on black, dark twins for the white lap list
PALETTE = ["#ffff00", "#ff50ff", "#00dc00", "#ff8c1a", "#ff4060", "#40c8ff"]
PALETTE_UI = ["#a08800", "#a020a0", "#007820", "#b05800", "#b00030", "#0060a0"]

# row: (title, unit, yrange or None)
ROWS = [
    ("Δ REF",  "s",    None),
    ("SPEED",  "km/h", None),
    ("THROTTLE", "%",  (-3, 108)),
    ("BRAKE",  "%",    (-3, 108)),
    ("STEER",  "",     (-1.1, 1.1)),
]
R_DELTA, R_SPEED, R_THR, R_BRK, R_STEER = range(5)


def lap_color(lap_no: int) -> str:
    return PALETTE[lap_no % len(PALETTE)]


def lap_color_ui(lap_no: int) -> str:
    return PALETTE_UI[lap_no % len(PALETTE_UI)]


class LapCompare(QtWidgets.QWidget):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self._seen_version = -1
        self._checked: set[int] = set()
        self._tick_n = 0
        self._hover_d = None
        self._lap_items: list = []          # plot items owned by completed laps

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ---- left: lap list — white i2 pane on grey chrome -------------
        left = QtWidgets.QFrame()
        left.setFixedWidth(268)
        ll = QtWidgets.QVBoxLayout(left)
        ll.setContentsMargins(6, 6, 2, 6)
        ll.setSpacing(6)
        cap = QtWidgets.QLabel("Круги  (галочка = наложить)")
        cap.setStyleSheet(f"color:{theme.TEXT};font-size:11px;font-weight:700;")
        ll.addWidget(cap)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["КРУГ", "ВРЕМЯ", "ОТСТАВ."])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self._on_item_changed)
        ll.addWidget(self.table, 1)

        legend = QtWidgets.QLabel(
            "★ эталон (лучший, белая линия)&nbsp;&nbsp;"
            f"<span style='color:#008080;font-weight:700'>■</span> текущий (live)")
        legend.setStyleSheet(f"color:{theme.TEXT};font-size:11px;")
        ll.addWidget(legend)
        self.hint = QtWidgets.QLabel("Δ REF: + медленнее · − быстрее эталона")
        self.hint.setStyleSheet(f"color:{theme.TEXT_DIM};font-size:10px;")
        ll.addWidget(self.hint)
        root.addWidget(left)

        # ---- right: distance-aligned strips ---------------------------
        gframe = QtWidgets.QFrame()
        gframe.setObjectName("panel")
        gl_ = QtWidgets.QVBoxLayout(gframe)
        gl_.setContentsMargins(6, 6, 6, 6)
        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setBackground(theme.BG)
        gl_.addWidget(self.glw)
        root.addWidget(gframe, 1)

        gl = self.glw.ci.layout
        gl.setColumnFixedWidth(0, 128)
        gl.setHorizontalSpacing(2)
        gl.setVerticalSpacing(2)
        gl.setContentsMargins(4, 4, 8, 4)

        self.plots, self.labels, self.vlines = [], [], []
        self.live_curves = []
        self._first = None
        cur_pen = pg.mkPen("#ffffff", width=1)
        for r, (name, unit, yr) in enumerate(ROWS):
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
            if yr:
                p.setYRange(*yr, padding=0)
            if r < len(ROWS) - 1:
                p.getAxis("bottom").setStyle(showValues=False)
            else:
                p.setLabel("bottom", "дистанция, м",
                           color=theme.FG_FAINT, size="8pt")
            if self._first is None:
                self._first = p
            else:
                p.setXLink(self._first)
            if r == R_DELTA or (yr and yr[0] < 0):
                p.addLine(y=0, pen=pg.mkPen(theme.GRID, width=1))
            vl = p.addLine(x=0, pen=cur_pen)
            vl.setVisible(False)
            self.vlines.append(vl)
            # live (in-progress lap) curve on top of everything
            lc = p.plot([], [], pen=pg.mkPen(LIVE_COL, width=1.4))
            lc.setZValue(20)
            self.live_curves.append(lc)
            self.plots.append(p)

        self._proxy = pg.SignalProxy(self.glw.scene().sigMouseMoved,
                                     rateLimit=60, slot=self._on_mouse)
        self._set_gutter(None, None)

    # ------------------------------------------------------------------
    # lap table
    # ------------------------------------------------------------------
    def _rebuild_table(self):
        st = self.store
        # newest lap gets auto-ticked; keep the overlay readable (≤4 ticks)
        if st.laps:
            newest = st.laps[-1].lap
            self._checked.add(newest)
            best_no = st.best.lap if st.best else None
            extra = [n for n in sorted(self._checked)
                     if n != newest and n != best_no]
            while len(self._checked) > 4 and extra:
                self._checked.discard(extra.pop(0))
        self._checked &= {r.lap for r in st.laps}

        self.table.blockSignals(True)
        self.table.setRowCount(len(st.laps))
        best = st.best
        bold = self.table.font()
        bold.setBold(True)
        for i, rec in enumerate(reversed(st.laps)):     # newest on top
            col = theme.TEXT if rec is best else lap_color_ui(rec.lap)
            star = " ★" if rec is best else ""
            it0 = QtWidgets.QTableWidgetItem(f"  {rec.lap}{star}")
            it0.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled |
                         QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            it0.setCheckState(QtCore.Qt.CheckState.Checked
                              if (rec.lap in self._checked or rec is best)
                              else QtCore.Qt.CheckState.Unchecked)
            it0.setForeground(pg.mkColor(col))
            if rec is best:
                it0.setFont(bold)
            it0.setData(QtCore.Qt.ItemDataRole.UserRole, rec.lap)
            it1 = QtWidgets.QTableWidgetItem(fmt_time(rec.time_s))
            it1.setForeground(pg.mkColor(theme.TEXT))
            if rec is best:
                it1.setFont(bold)
            gap = rec.time_s - best.time_s if best else 0.0
            it2 = QtWidgets.QTableWidgetItem(
                "—" if rec is best else f"+{gap:.3f}")
            it2.setForeground(pg.mkColor(
                "#808080" if rec is best else "#b00000"))
            self.table.setItem(i, 0, it0)
            self.table.setItem(i, 1, it1)
            self.table.setItem(i, 2, it2)
        self.table.blockSignals(False)

    def _on_item_changed(self, item):
        if item.column() != 0:
            return
        lap_no = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if item.checkState() == QtCore.Qt.CheckState.Checked:
            self._checked.add(lap_no)
        else:
            self._checked.discard(lap_no)
        self._redraw_laps()

    # ------------------------------------------------------------------
    # curves
    # ------------------------------------------------------------------
    def _redraw_laps(self):
        for p, it in self._lap_items:
            try:
                p.removeItem(it)
            except Exception:
                pass
        self._lap_items = []

        st = self.store
        best = st.best
        if best is None:
            return
        show = [r for r in st.laps if r.lap in self._checked or r is best]
        dmax = float(best.dist[-1])
        dabs = 1.0
        for rec in show:
            is_ref = rec is best
            col = REF_COL if is_ref else lap_color(rec.lap)
            pen = pg.mkPen(col, width=1.6 if is_ref else 1.1)
            dmax = max(dmax, float(rec.dist[-1]))
            series = [
                (R_SPEED, rec.speed), (R_THR, rec.thr),
                (R_BRK, rec.brk), (R_STEER, rec.steer),
            ]
            if not is_ref:
                dl = rec.delta_to(best)
                dabs = max(dabs, float(np.max(np.abs(dl))))
                series.append((R_DELTA, dl))
            for row, y in series:
                c = self.plots[row].plot(rec.dist, y, pen=pen)
                c.setZValue(10 if is_ref else 5)
                self._lap_items.append((self.plots[row], c))

        self._first.setXRange(0, dmax, padding=0.01)
        self.plots[R_DELTA].setYRange(-min(dabs, 15.0) * 1.15,
                                      min(dabs, 15.0) * 1.15, padding=0)
        smax = max(float(np.max(r.speed)) for r in show)
        self.plots[R_SPEED].setYRange(0, smax * 1.06, padding=0)

    def _update_live(self, f):
        cur = self.store.current_arrays()
        best = self.store.best
        if cur is None:
            for lc in self.live_curves:
                lc.setData([], [])
            return None
        d, t, spd, thr, brk, steer = cur
        step = max(1, len(d) // 1500)
        d2 = d[::step]
        self.live_curves[R_SPEED].setData(d2, spd[::step])
        self.live_curves[R_THR].setData(d2, thr[::step])
        self.live_curves[R_BRK].setData(d2, brk[::step])
        self.live_curves[R_STEER].setData(d2, steer[::step])
        if best is not None and len(d2) > 2:
            tref = np.interp(d2, best.dist, best.t_at_d)
            self.live_curves[R_DELTA].setData(d2, (t[::step] - t[0]) - tref)
        else:
            self.live_curves[R_DELTA].setData([], [])
        if best is None and len(d) > 2:
            self._first.setXRange(0, float(d[-1]) * 1.05, padding=0)
            self.plots[R_SPEED].setYRange(0, max(100.0, float(np.max(spd)) * 1.06),
                                          padding=0)
        return cur

    # ------------------------------------------------------------------
    # hover cursor + gutter values
    # ------------------------------------------------------------------
    def _on_mouse(self, evt):
        try:
            pos = evt[0]
            if self._first.sceneBoundingRect().contains(pos):
                self._hover_d = float(self._first.vb.mapSceneToView(pos).x())
            else:
                self._hover_d = None
        except Exception:
            self._hover_d = None

    def leaveEvent(self, e):
        self._hover_d = None
        super().leaveEvent(e)

    def _set_gutter(self, ref_vals, live_vals):
        for r, (name, unit, _yr) in enumerate(ROWS):
            rv = "—" if ref_vals is None else ref_vals[r]
            lv = "—" if live_vals is None else live_vals[r]
            self.labels[r].setText(
                "<div style='line-height:1.1'>"
                f"<span style='color:{theme.FG_DIM};font-size:8pt;font-weight:700;"
                f"letter-spacing:1px'>{name}"
                f"<span style='color:{theme.FG_FAINT}'> {unit}</span></span><br>"
                f"<span style='color:{REF_COL};font-size:11pt;font-weight:700'>{rv}</span>"
                f"<span style='color:{theme.FG_FAINT}'> / </span>"
                f"<span style='color:{LIVE_COL};font-size:11pt;font-weight:700'>{lv}</span>"
                "</div>")

    @staticmethod
    def _fmt_row(r, val):
        if val is None:
            return "—"
        if r == R_DELTA:
            return f"{val:+.2f}"
        if r == R_STEER:
            return f"{val:+.2f}"
        return f"{val:.0f}"

    # ------------------------------------------------------------------
    def update_frame(self, f):
        self._tick_n += 1
        if not self.isVisible():
            return
        if self.store.version != self._seen_version:
            self._seen_version = self.store.version
            self._rebuild_table()
            self._redraw_laps()
        if self._tick_n % 3:
            return
        cur = self._update_live(f)

        best = self.store.best
        # cursor + gutter readout
        if self._hover_d is not None:
            for vl in self.vlines:
                vl.setVisible(True)
                vl.setValue(self._hover_d)
            ref_vals = live_vals = None
            if best is not None:
                x = self._hover_d
                ref_vals = [self._fmt_row(R_DELTA, 0.0),
                            self._fmt_row(R_SPEED, np.interp(x, best.dist, best.speed)),
                            self._fmt_row(R_THR, np.interp(x, best.dist, best.thr)),
                            self._fmt_row(R_BRK, np.interp(x, best.dist, best.brk)),
                            self._fmt_row(R_STEER, np.interp(x, best.dist, best.steer))]
            if cur is not None:
                d, t, spd, thr, brk, steer = cur
                if len(d) > 2 and d[0] <= self._hover_d <= d[-1]:
                    x = self._hover_d
                    if best is not None:
                        dl = float(np.interp(x, d, t - t[0]) -
                                   np.interp(x, best.dist, best.t_at_d))
                    else:
                        dl = None
                    live_vals = [self._fmt_row(R_DELTA, dl),
                                 self._fmt_row(R_SPEED, np.interp(x, d, spd)),
                                 self._fmt_row(R_THR, np.interp(x, d, thr)),
                                 self._fmt_row(R_BRK, np.interp(x, d, brk)),
                                 self._fmt_row(R_STEER, np.interp(x, d, steer))]
            self._set_gutter(ref_vals, live_vals)
        else:
            for vl in self.vlines:
                vl.setVisible(False)
            ref_vals = None
            if best is not None:
                ref_vals = ["0.00", self._fmt_row(R_SPEED, None), "—", "—", "—"]
                x = min(f.lap_dist, float(best.dist[-1])) if f.lap_dist > 0 else None
                if x is not None:
                    ref_vals = [self._fmt_row(R_DELTA, 0.0),
                                self._fmt_row(R_SPEED, np.interp(x, best.dist, best.speed)),
                                self._fmt_row(R_THR, np.interp(x, best.dist, best.thr)),
                                self._fmt_row(R_BRK, np.interp(x, best.dist, best.brk)),
                                self._fmt_row(R_STEER, np.interp(x, best.dist, best.steer))]
            ld = self.store.live_delta(f)
            live_vals = [self._fmt_row(R_DELTA, ld),
                         self._fmt_row(R_SPEED, f.speed),
                         self._fmt_row(R_THR, f.throttle * 100),
                         self._fmt_row(R_BRK, f.brake * 100),
                         self._fmt_row(R_STEER, f.steer)]
            self._set_gutter(ref_vals, live_vals)

    def showEvent(self, e):
        # force a rebuild next tick when the tab becomes visible
        self._seen_version = -1
        super().showEvent(e)
