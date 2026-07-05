"""Main window in the classic MoTeC i2 layout: menu bar and toolbar on grey
chrome, black worksheet area, worksheet tabs at the BOTTOM and a status bar
carrying the connection / track / session readouts."""
from __future__ import annotations

import os
import time

from PyQt6 import QtCore, QtGui, QtWidgets

from sources import SourceManager
from sources.laps import LapStore
from . import theme
from .channel_graphs import ChannelGraphs
from .gauges import GaugePanel
from .tyres import TyrePanel
from .trackmap import TrackMap
from .gmeter import GMeter
from .numeric import NumericReport
from .channels import ChannelBrowser
from .lapcompare import LapCompare
from .histogram import HistogramSheet


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, f1_port=20777, manager=None):
        super().__init__()
        self.setWindowTitle("Phantom i2 — Sim Telemetry")
        self.resize(1600, 980)
        self.setStyleSheet(theme.QSS)

        self.mgr = manager if manager is not None else SourceManager(f1_port=f1_port)
        self.mgr.start()
        self._paused = False

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 2)
        root.setSpacing(4)

        # ---- worksheets (tabs at the bottom, i2 style) ----------------
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setTabPosition(QtWidgets.QTabWidget.TabPosition.South)
        root.addWidget(self.tabs, 1)

        dash = QtWidgets.QWidget()
        body = QtWidgets.QHBoxLayout(dash)
        body.setContentsMargins(4, 4, 4, 4)
        body.setSpacing(4)

        # left column: graphs (stretch) + bottom strip
        left = QtWidgets.QVBoxLayout()
        left.setSpacing(4)
        self.graphs = ChannelGraphs()
        gframe = QtWidgets.QFrame()
        gframe.setObjectName("panel")
        gl = QtWidgets.QVBoxLayout(gframe)
        gl.setContentsMargins(2, 2, 2, 2)
        gl.addWidget(self.graphs)
        left.addWidget(gframe, 1)

        bottomw = QtWidgets.QWidget()
        bottomw.setFixedHeight(252)
        bl = QtWidgets.QHBoxLayout(bottomw)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)
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
        right.setSpacing(4)
        self.gauges = GaugePanel()
        right.addWidget(self.gauges)
        self.tyres = TyrePanel()
        right.addWidget(self.tyres)
        rw = QtWidgets.QWidget()
        rw.setLayout(right)
        rw.setFixedWidth(380)
        body.addWidget(rw)

        self.tabs.addTab(dash, "График")

        # lap store + i2-style lap comparison worksheet
        self.laps = LapStore()
        self.lapcmp = LapCompare(self.laps)
        self.tabs.addTab(self.lapcmp, "Круги / Дельта")

        # i2-style histograms
        self.hist = HistogramSheet()
        self.tabs.addTab(self.hist, "Гистограммы")

        # the complete channel list
        self.browser = ChannelBrowser()
        self.tabs.addTab(self.browser, "Все каналы")

        # ---- i2 chrome: menus, toolbar, status bar --------------------
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()

        # render loop ~30 Hz
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    # ------------------------------------------------------------------
    def _build_menus(self):
        mb = self.menuBar()

        m_file = mb.addMenu("Файл")
        act_shot = QtGui.QAction("Сохранить скриншот…", self)
        act_shot.setShortcut("Ctrl+S")
        act_shot.triggered.connect(self._screenshot)
        m_file.addAction(act_shot)
        m_file.addSeparator()
        act_exit = QtGui.QAction("Выход", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        m_tools = mb.addMenu("Инструменты")
        self.act_pause = QtGui.QAction("Пауза экрана", self)
        self.act_pause.setCheckable(True)
        self.act_pause.setShortcut("Ctrl+P")
        self.act_pause.toggled.connect(self._toggle_pause)
        m_tools.addAction(self.act_pause)
        act_reset = QtGui.QAction("Сбросить круги", self)
        act_reset.triggered.connect(self._reset_laps)
        m_tools.addAction(act_reset)

        m_win = mb.addMenu("Окно")
        group = QtGui.QActionGroup(self)
        names = [("График", "F2"), ("Круги / Дельта", "F3"),
                 ("Гистограммы", "F4"), ("Все каналы", "F5")]
        self._ws_actions = []
        for i, (name, key) in enumerate(names):
            a = QtGui.QAction(name, self)
            a.setCheckable(True)
            a.setShortcut(key)
            a.setChecked(i == 0)
            a.triggered.connect(lambda _c, idx=i: self.tabs.setCurrentIndex(idx))
            group.addAction(a)
            m_win.addAction(a)
            self._ws_actions.append(a)
        self.tabs.currentChanged.connect(self._sync_ws_actions)

        m_help = mb.addMenu("Справка")
        act_about = QtGui.QAction("О программе", self)
        act_about.triggered.connect(self._about)
        m_help.addAction(act_about)

    def _build_toolbar(self):
        tb = QtWidgets.QToolBar("Основная")
        tb.setMovable(False)
        tb.setFloatable(False)
        self.addToolBar(tb)
        tb.addAction(self.act_pause)
        shot = QtGui.QAction("Скриншот", self)
        shot.triggered.connect(self._screenshot)
        tb.addAction(shot)
        tb.addSeparator()
        for a in self._ws_actions:
            tb.addAction(a)

    def _build_statusbar(self):
        sb = self.statusBar()
        self.sb_conn = QtWidgets.QLabel("нет данных")
        self.sb_track = QtWidgets.QLabel("—")
        self.sb_sess = QtWidgets.QLabel("")
        self.sb_lap = QtWidgets.QLabel("")
        sb.addWidget(self.sb_conn)
        sb.addWidget(self._sb_sep())
        sb.addWidget(self.sb_track)
        sb.addWidget(self._sb_sep())
        sb.addWidget(self.sb_sess)
        self.sb_rate = QtWidgets.QLabel("")
        sb.addPermanentWidget(self.sb_lap)
        sb.addPermanentWidget(self._sb_sep())
        sb.addPermanentWidget(self.sb_rate)
        self._frames = 0
        self._rate_t0 = time.monotonic()

    @staticmethod
    def _sb_sep():
        s = QtWidgets.QLabel("|")
        s.setStyleSheet(f"color:{theme.CHROME_SH};")
        return s

    # ------------------------------------------------------------------
    def _sync_ws_actions(self, idx):
        if 0 <= idx < len(self._ws_actions):
            self._ws_actions[idx].setChecked(True)

    def _toggle_pause(self, on):
        self._paused = on

    def _reset_laps(self):
        self.laps.__init__()
        self.lapcmp._seen_version = -1

    def _screenshot(self):
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
        name = f"telemetry_{time.strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(desk if os.path.isdir(desk) else os.getcwd(), name)
        self.grab().save(path)
        self.statusBar().showMessage(f"Скриншот: {path}", 4000)

    def _about(self):
        QtWidgets.QMessageBox.about(
            self, "Phantom i2",
            "Phantom i2 — Sim Telemetry\n\n"
            "Живая телеметрия iRacing / Le Mans Ultimate / F1 25\n"
            "в классическом стиле дата-логгера.\n\n"
            "Часть экосистемы Phantom.")

    # ------------------------------------------------------------------
    def _tick(self):
        f = self.mgr.poll()
        status = self.mgr.status()
        # record the lap and, when the sim itself gives no live delta
        # (LMU / F1), compute it against our stored best lap
        self.laps.push(f)
        if abs(f.delta_best) < 1e-9:
            ld = self.laps.live_delta(f)
            if ld is not None:
                f.delta_best = ld
        if not self._paused:
            self.lapcmp.update_frame(f)
            self.hist.update_frame(f)
            self.graphs.push(f)
            self.graphs.redraw(f)
            self.gauges.update_frame(f)
            self.tyres.update_frame(f)
            self.trackmap.update_frame(f)
            self.gmeter.update_frame(f)
            self.numeric.update_frame(f)
            self.browser.update_frame(f)
        self._update_statusbar(f, status)

    def _update_statusbar(self, f, status):
        if f.connected:
            self.sb_conn.setText(f"● {f.game}")
            self.sb_conn.setStyleSheet("color:#007000;font-weight:700;padding:0 6px;")
            self.sb_track.setText(f.track or "—")
            self.sb_sess.setText(f.session or "")
            lap = f"Круг {f.lap}"
            if f.total_laps:
                lap += f"/{f.total_laps}"
            if f.position:
                lap += f" · P{f.position}"
            self.sb_lap.setText(lap)
        else:
            err = (status.get("error") or "").strip()
            self.sb_conn.setText("○ ожидание данных")
            self.sb_conn.setStyleSheet(f"color:{theme.TEXT_DIM};padding:0 6px;")
            self.sb_track.setText("—" if not err else err[:60])
            self.sb_sess.setText("")
            self.sb_lap.setText("")
        self._frames += 1
        now = time.monotonic()
        if now - self._rate_t0 >= 1.0:
            self.sb_rate.setText(f"{self._frames / (now - self._rate_t0):.0f} Гц")
            self._frames = 0
            self._rate_t0 = now

    def closeEvent(self, e):
        try:
            self.timer.stop()
            self.mgr.stop()
        except Exception:
            pass
        super().closeEvent(e)
