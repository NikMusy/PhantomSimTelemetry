"""Main worksheet window — assembles the header, channel graphs, gauges, tyre
panel and track map, and drives them from the SourceManager at ~30 Hz."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from sources import SourceManager
from . import theme
from .channel_graphs import ChannelGraphs
from .gauges import GaugePanel
from .tyres import TyrePanel
from .trackmap import TrackMap
from .gmeter import GMeter
from .numeric import NumericReport
from .channels import ChannelBrowser


class StatusDot(QtWidgets.QWidget):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._on = False
        self._label = label
        self.setFixedSize(86, 20)

    def set(self, on):
        if on != self._on:
            self._on = on
            self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        col = QtGui.QColor(theme.THROTTLE if self._on else theme.FG_FAINT)
        p.setBrush(col)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawEllipse(0, 5, 10, 10)
        p.setPen(QtGui.QColor(theme.FG if self._on else theme.FG_DIM))
        f = p.font(); f.setPointSize(9); f.setBold(self._on); p.setFont(f)
        p.drawText(QtCore.QRectF(16, 0, 70, 20),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   self._label)
        p.end()


class Header(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.setFixedHeight(56)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(16, 6, 16, 6)
        lay.setSpacing(18)

        brand = QtWidgets.QLabel("LIVE TELEMETRY")
        brand.setStyleSheet(f"color:{theme.ACCENT};font-size:18px;font-weight:800;"
                            "letter-spacing:2px;")
        lay.addWidget(brand)

        self.game = self._big("—", theme.GEAR)
        lay.addWidget(self.game)
        lay.addWidget(self._sep())

        self.track = self._big("waiting for a session…", theme.FG)
        lay.addWidget(self.track)
        lay.addWidget(self._sep())
        self.session = self._big("", theme.FG_DIM)
        lay.addWidget(self.session)

        lay.addStretch(1)
        self.dot_lmu = StatusDot("LMU")
        self.dot_f1 = StatusDot("F1 25")
        lay.addWidget(self.dot_lmu)
        lay.addWidget(self.dot_f1)

    def _big(self, text, color):
        lab = QtWidgets.QLabel(text)
        lab.setStyleSheet(f"color:{color};font-size:15px;font-weight:700;")
        return lab

    def _sep(self):
        s = QtWidgets.QLabel("•")
        s.setStyleSheet(f"color:{theme.FG_FAINT};font-size:14px;")
        return s

    def update_frame(self, f, status):
        self.game.setText(f.game if f.connected else "—")
        if f.connected:
            self.track.setText(f.track or "—")
            self.session.setText(f.session or "")
        else:
            err = (status.get("error") or "").strip()
            self.track.setText("ожидание данных…" if not err else "нет связи")
            self.session.setText(err[:60])
        self.dot_lmu.set(status["lmu"])
        self.dot_f1.set(status["f1"])


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, f1_port=20777, manager=None):
        super().__init__()
        self.setWindowTitle("Live Telemetry — iRacing / LMU / F1 25")
        self.resize(1600, 980)
        self.setStyleSheet(theme.QSS)

        self.mgr = manager if manager is not None else SourceManager(f1_port=f1_port)
        self.mgr.start()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.header = Header()
        root.addWidget(self.header)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet(
            f"QTabBar::tab{{background:{theme.PANEL};color:{theme.FG_DIM};padding:7px 18px;"
            f"font-size:12px;font-weight:700;letter-spacing:1px;border:1px solid {theme.BORDER};"
            f"border-bottom:none;border-top-left-radius:6px;border-top-right-radius:6px;}}"
            f"QTabBar::tab:selected{{background:{theme.PANEL_HI};color:{theme.ACCENT};}}"
            f"QTabWidget::pane{{border:1px solid {theme.BORDER};border-radius:4px;top:-1px;}}")
        root.addWidget(self.tabs, 1)

        dash = QtWidgets.QWidget()
        body = QtWidgets.QHBoxLayout(dash)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)

        # left column: graphs (stretch) + track map
        left = QtWidgets.QVBoxLayout()
        left.setSpacing(8)
        self.graphs = ChannelGraphs()
        gframe = QtWidgets.QFrame()
        gframe.setObjectName("panel")
        gl = QtWidgets.QVBoxLayout(gframe)
        gl.setContentsMargins(6, 6, 6, 6)
        gl.addWidget(self.graphs)
        left.addWidget(gframe, 1)

        # bottom strip: track map + G-G meter + dense data table
        bottomw = QtWidgets.QWidget()
        bottomw.setFixedHeight(252)
        bl = QtWidgets.QHBoxLayout(bottomw)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)
        self.trackmap = TrackMap()
        self.trackmap.setFixedWidth(300)
        self.gmeter = GMeter()
        self.gmeter.setFixedWidth(252)
        self.numeric = NumericReport()
        bl.addWidget(self.trackmap)
        bl.addWidget(self.gmeter)
        bl.addWidget(self.numeric, 1)
        left.addWidget(bottomw)
        body.addLayout(left, 1)

        # right column: gauges + tyres
        right = QtWidgets.QVBoxLayout()
        right.setSpacing(8)
        self.gauges = GaugePanel()
        right.addWidget(self.gauges)
        self.tyres = TyrePanel()
        right.addWidget(self.tyres)
        rw = QtWidgets.QWidget()
        rw.setLayout(right)
        rw.setFixedWidth(380)
        body.addWidget(rw)

        self.tabs.addTab(dash, "  ДАШБОРД  ")

        # second tab: the complete iRacing channel list
        self.browser = ChannelBrowser()
        self.tabs.addTab(self.browser, "  ВСЕ КАНАЛЫ  ")

        # render loop ~30 Hz
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _tick(self):
        f = self.mgr.poll()
        status = self.mgr.status()
        self.graphs.push(f)
        self.graphs.redraw(f)
        self.gauges.update_frame(f)
        self.tyres.update_frame(f)
        self.trackmap.update_frame(f)
        self.gmeter.update_frame(f)
        self.numeric.update_frame(f)
        self.browser.update_frame(f)
        self.header.update_frame(f, status)

    def closeEvent(self, e):
        try:
            self.timer.stop()
            self.mgr.stop()
        except Exception:
            pass
        super().closeEvent(e)
