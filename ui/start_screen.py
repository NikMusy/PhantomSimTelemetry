"""Start screen — pick the game and the connection, MoTeC-dark styled.

LMU connects to an LMU Pit Wall server over the network (Radmin IP + port), or
optionally to this PC's shared memory. F1 25 listens for UDP telemetry locally.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from sources import config
from . import theme


class GameCard(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal()

    def __init__(self, key, title, subtitle, accent, parent=None):
        super().__init__(parent)
        self.key = key
        self.accent = accent
        self._selected = False
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(260, 178)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(4)
        self.tag = QtWidgets.QLabel(key)
        self.tag.setStyleSheet(f"color:{accent};font-size:11px;font-weight:700;"
                               "letter-spacing:2px;")
        t = QtWidgets.QLabel(title)
        t.setStyleSheet(f"color:{theme.FG};font-size:23px;font-weight:800;"
                        "line-height:1.0;")
        s = QtWidgets.QLabel(subtitle)
        s.setStyleSheet(f"color:{theme.FG_DIM};font-size:12px;")
        s.setWordWrap(True)
        lay.addWidget(self.tag)
        lay.addWidget(t)
        lay.addStretch(1)
        lay.addWidget(s)
        self._restyle()

    def setSelected(self, on):
        self._selected = on
        self._restyle()

    def _restyle(self):
        border = self.accent if self._selected else theme.BORDER
        bg = theme.PANEL_HI if self._selected else theme.PANEL
        self.setStyleSheet(
            f"GameCard{{background:{bg};border:2px solid {border};border-radius:12px;}}")

    def mousePressEvent(self, _):
        self.clicked.emit()


class StartScreen(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live Telemetry — выбор игры")
        self.setStyleSheet(theme.QSS)
        self.setModal(True)
        self.setFixedWidth(880)
        self.cfg = config.load()
        self.manager = None
        self.game = self.cfg.get("last_game", "LMU")

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(18)

        brand = QtWidgets.QLabel("LIVE TELEMETRY")
        brand.setStyleSheet(f"color:{theme.ACCENT};font-size:24px;font-weight:800;"
                            "letter-spacing:3px;")
        sub = QtWidgets.QLabel("Выберите симулятор и подключитесь")
        sub.setStyleSheet(f"color:{theme.FG_DIM};font-size:13px;")
        root.addWidget(brand)
        root.addWidget(sub)

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(16)
        self.card_lmu = GameCard("LMU", "Le Mans\nUltimate",
                                 "Подключение по сети (Radmin IP + порт) "
                                 "к серверу LMU Pit Wall", theme.GEAR)
        self.card_f1 = GameCard("F1 25", "F1 25",
                                "Телеметрия по UDP — игра шлёт данные "
                                "на этот ПК", theme.SPEED)
        self.card_iracing = GameCard("iRACING", "iRacing",
                                     "Локально с этого ПК + раздача стратегу "
                                     "по Radmin, или подключение к хосту",
                                     theme.BRAKE)
        self.card_lmu.clicked.connect(lambda: self._select("LMU"))
        self.card_f1.clicked.connect(lambda: self._select("F1 25"))
        self.card_iracing.clicked.connect(lambda: self._select("iRacing"))
        cards.addWidget(self.card_lmu)
        cards.addWidget(self.card_f1)
        cards.addWidget(self.card_iracing)
        cards.addStretch(1)
        root.addLayout(cards)

        # --- connection settings (stacked) ---
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self._lmu_panel())       # index 0
        self.stack.addWidget(self._f1_panel())        # index 1
        self.stack.addWidget(self._iracing_panel())   # index 2
        box = QtWidgets.QFrame()
        box.setObjectName("panel")
        bl = QtWidgets.QVBoxLayout(box)
        bl.setContentsMargins(16, 14, 16, 14)
        bl.addWidget(self.stack)
        root.addWidget(box)

        self.err = QtWidgets.QLabel("")
        self.err.setStyleSheet(f"color:{theme.BRAKE};font-size:12px;")
        root.addWidget(self.err)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        self.connect_btn = QtWidgets.QPushButton("ПОДКЛЮЧИТЬСЯ  ▶")
        self.connect_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setFixedHeight(44)
        self.connect_btn.setStyleSheet(
            f"QPushButton{{background:{theme.ACCENT};color:#04141c;font-size:14px;"
            f"font-weight:800;letter-spacing:1px;border:none;border-radius:8px;"
            f"padding:0 28px;}}"
            f"QPushButton:hover{{background:#6fe0ff;}}")
        self.connect_btn.clicked.connect(self._connect)
        btns.addWidget(self.connect_btn)
        root.addLayout(btns)

        self._select(self.game)

    # ----------------------------------------------------------------
    def _lmu_panel(self):
        w = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)

        g.addWidget(self._cap("IP-АДРЕС (RADMIN)"), 0, 0)
        g.addWidget(self._cap("ПОРТ"), 0, 1)
        self.lmu_host = QtWidgets.QLineEdit(str(self.cfg.get("lmu_host", "")))
        self.lmu_host.setPlaceholderText("например 26.x.x.x")
        self.lmu_port = QtWidgets.QLineEdit(str(self.cfg.get("lmu_port", 8000)))
        self.lmu_port.setValidator(QtGui.QIntValidator(1, 65535, self))
        for e in (self.lmu_host, self.lmu_port):
            e.setFixedHeight(34)
            e.setStyleSheet(self._edit_qss())
        g.addWidget(self.lmu_host, 1, 0)
        g.addWidget(self.lmu_port, 1, 1)

        self.lmu_local = QtWidgets.QCheckBox(
            "Локально — читать shared memory этого ПК (без сети)")
        self.lmu_local.setChecked(bool(self.cfg.get("lmu_local", False)))
        self.lmu_local.setStyleSheet(f"color:{theme.FG_DIM};font-size:12px;")
        self.lmu_local.toggled.connect(self._toggle_local)
        g.addWidget(self.lmu_local, 2, 0, 1, 2)

        hint = QtWidgets.QLabel(
            "На игровом ПК должен быть запущен LMU Pit Wall server "
            "(порт 8000). Введите его Radmin-IP и порт.")
        hint.setStyleSheet(f"color:{theme.FG_FAINT};font-size:11px;")
        hint.setWordWrap(True)
        g.addWidget(hint, 3, 0, 1, 2)
        self._toggle_local(self.lmu_local.isChecked())
        return w

    def _f1_panel(self):
        w = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)
        g.addWidget(self._cap("UDP-ПОРТ"), 0, 0)
        self.f1_port = QtWidgets.QLineEdit(str(self.cfg.get("f1_port", 20777)))
        self.f1_port.setValidator(QtGui.QIntValidator(1, 65535, self))
        self.f1_port.setFixedHeight(34)
        self.f1_port.setFixedWidth(140)
        self.f1_port.setStyleSheet(self._edit_qss())
        g.addWidget(self.f1_port, 1, 0)
        hint = QtWidgets.QLabel(
            "В F1 25: Settings → Telemetry → UDP Telemetry = On, порт = 20777, "
            "60 Hz. Если игра на другом ПК — укажи в ней Radmin-IP этого ПК "
            "как адрес получателя.")
        hint.setStyleSheet(f"color:{theme.FG_FAINT};font-size:11px;")
        hint.setWordWrap(True)
        g.addWidget(hint, 2, 0, 1, 2)
        return w

    def _iracing_panel(self):
        w = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)

        g.addWidget(self._cap("IP-АДРЕС ХОСТА (RADMIN)"), 0, 0)
        g.addWidget(self._cap("ПОРТ"), 0, 1)
        self.ir_host = QtWidgets.QLineEdit(str(self.cfg.get("iracing_host", "")))
        self.ir_host.setPlaceholderText("например 26.x.x.x")
        self.ir_port = QtWidgets.QLineEdit(str(self.cfg.get("iracing_port", 8100)))
        self.ir_port.setValidator(QtGui.QIntValidator(1, 65535, self))
        for e in (self.ir_host, self.ir_port):
            e.setFixedHeight(34)
            e.setStyleSheet(self._edit_qss())
        g.addWidget(self.ir_host, 1, 0)
        g.addWidget(self.ir_port, 1, 1)

        self.ir_local = QtWidgets.QCheckBox(
            "Локально — читать iRacing этого ПК (я за рулём)")
        self.ir_local.setChecked(bool(self.cfg.get("iracing_local", True)))
        self.ir_local.setStyleSheet(f"color:{theme.FG_DIM};font-size:12px;")
        self.ir_local.toggled.connect(self._toggle_iracing_local)
        g.addWidget(self.ir_local, 2, 0, 1, 2)

        self.ir_share = QtWidgets.QCheckBox(
            "Раздавать стратегу по Radmin (на указанном порту)")
        self.ir_share.setChecked(bool(self.cfg.get("iracing_share", True)))
        self.ir_share.setStyleSheet(f"color:{theme.FG_DIM};font-size:12px;")
        g.addWidget(self.ir_share, 3, 0, 1, 2)

        hint = QtWidgets.QLabel(
            "За рулём: «Локально» + «Раздавать» — порт 8100. Стратег: снять "
            "«Локально», вписать твой Radmin-IP и тот же порт.")
        hint.setStyleSheet(f"color:{theme.FG_FAINT};font-size:11px;")
        hint.setWordWrap(True)
        g.addWidget(hint, 4, 0, 1, 2)
        self._toggle_iracing_local(self.ir_local.isChecked())
        return w

    def _toggle_iracing_local(self, on):
        # local mode: host not needed (we read this PC); port = share port
        self.ir_host.setDisabled(on)
        self.ir_share.setDisabled(not on)

    def _toggle_local(self, on):
        self.lmu_host.setDisabled(on)
        self.lmu_port.setDisabled(on)

    def _select(self, game):
        self.game = game
        self.card_lmu.setSelected(game == "LMU")
        self.card_f1.setSelected(game == "F1 25")
        self.card_iracing.setSelected(game == "iRacing")
        self.stack.setCurrentIndex({"LMU": 0, "F1 25": 1, "iRacing": 2}.get(game, 0))
        self.err.setText("")

    # ----------------------------------------------------------------
    def _connect(self):
        from sources import SingleManager
        self.err.setText("")
        if self.game == "LMU":
            local = self.lmu_local.isChecked()
            self.cfg["lmu_local"] = local
            if local:
                from sources.lmu_source import LMUSource
                src = LMUSource()
            else:
                host = self.lmu_host.text().strip()
                if not host:
                    self.err.setText("Укажите IP-адрес (из Radmin).")
                    return
                port = int(self.lmu_port.text() or 8000)
                self.cfg["lmu_host"] = host
                self.cfg["lmu_port"] = port
                from sources.lmu_net_source import LMUNetSource
                src = LMUNetSource(host, port)
            self.manager = SingleManager(src, "LMU")
        elif self.game == "F1 25":
            port = int(self.f1_port.text() or 20777)
            self.cfg["f1_port"] = port
            from sources.f1_source import F1Source
            src = F1Source(port=port)
            self.manager = SingleManager(src, "F1 25")
        else:  # iRacing
            local = self.ir_local.isChecked()
            port = int(self.ir_port.text() or 8100)
            self.cfg["iracing_local"] = local
            self.cfg["iracing_port"] = port
            if local:
                share = self.ir_share.isChecked()
                self.cfg["iracing_share"] = share
                from sources.iracing_source import IRacingSource
                src = IRacingSource(share_port=port if share else None)
            else:
                host = self.ir_host.text().strip()
                if not host:
                    self.err.setText("Укажите Radmin-IP хоста.")
                    return
                self.cfg["iracing_host"] = host
                from sources.net_frame import NetFrameSource
                src = NetFrameSource(host, port, "iRacing")
            self.manager = SingleManager(src, "iRacing")

        self.cfg["last_game"] = self.game
        config.save(self.cfg)
        self.accept()

    # ----------------------------------------------------------------
    @staticmethod
    def _cap(text):
        lab = QtWidgets.QLabel(text)
        lab.setStyleSheet(f"color:{theme.FG_DIM};font-size:10px;font-weight:600;"
                          "letter-spacing:1px;")
        return lab

    @staticmethod
    def _edit_qss():
        return (f"QLineEdit{{background:{theme.BG};color:{theme.FG};"
                f"border:1px solid {theme.BORDER};border-radius:6px;padding:0 10px;"
                f"font-size:14px;}}"
                f"QLineEdit:focus{{border:1px solid {theme.ACCENT};}}"
                f"QLineEdit:disabled{{color:{theme.FG_FAINT};}}")
