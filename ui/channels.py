"""All-Channels browser — the complete iRacing telemetry variable list, live.

Every channel iRacing exposes (arrays expanded per car/wheel) shown in a fast,
filterable table: Channel | Value | Unit. This is the ATLAS-style "see
everything" view. Backed by a QAbstractTableModel so thousands of rows update
smoothly (only visible cells repaint)."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme


def _fmt(v) -> str:
    try:
        fv = float(v)
    except Exception:
        return str(v)
    if fv == int(fv) and abs(fv) < 1e9:
        return str(int(fv))
    if abs(fv) >= 1000:
        return f"{fv:.1f}"
    return f"{fv:.4f}"


class ChannelModel(QtCore.QAbstractTableModel):
    HEADERS = ["Канал", "Значение", "Ед."]

    def __init__(self):
        super().__init__()
        self._all = []          # all channel names (sorted)
        self._names = []        # filtered visible names
        self._values = {}
        self._units = {}
        self._filter = ""
        self._mono = QtGui.QFont("Consolas", 10)

    # ---- Qt model API ----------------------------------------------
    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._names)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 3

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.DisplayRole and orientation == QtCore.Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        name = self._names[index.row()]
        col = index.column()
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return name
            if col == 1:
                return _fmt(self._values.get(name, 0.0))
            return self._units.get(name, "")
        if role == QtCore.Qt.ItemDataRole.FontRole and col == 1:
            return self._mono
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole and col == 1:
            return int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if col == 0:
                return QtGui.QColor(theme.TEXT)
            if col == 1:
                return QtGui.QColor(theme.ACCENT_CHROME)
            return QtGui.QColor("#707070")
        return None

    # ---- updates ----------------------------------------------------
    def set_values(self, values: dict, units: dict):
        if units:
            self._units = units
        if len(values) != len(self._all):
            self._rebuild_all(values)
        self._values = values
        if self._names:
            self.dataChanged.emit(self.index(0, 1),
                                  self.index(len(self._names) - 1, 1),
                                  [QtCore.Qt.ItemDataRole.DisplayRole])

    def set_filter(self, text: str):
        self._filter = (text or "").strip().lower()
        self._apply_filter()

    def _rebuild_all(self, values):
        self._all = sorted(values.keys(), key=str.lower)
        self._apply_filter()

    def _apply_filter(self):
        self.beginResetModel()
        if self._filter:
            self._names = [n for n in self._all if self._filter in n.lower()]
        else:
            self._names = list(self._all)
        self.endResetModel()

    def visible(self) -> int:
        return len(self._names)


class ChannelBrowser(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw = {}
        self._units = {}

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(10)
        title = QtWidgets.QLabel("Все каналы")
        title.setStyleSheet(f"color:{theme.ACCENT_CHROME};font-size:13px;"
                            "font-weight:700;letter-spacing:1px;")
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("поиск канала…  (напр. tyre, fuel, CarIdx)")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(24)
        self.count = QtWidgets.QLabel("0 каналов")
        self.count.setStyleSheet(f"color:{theme.TEXT_DIM};font-size:12px;")
        top.addWidget(title)
        top.addWidget(self.search, 1)
        top.addWidget(self.count)
        root.addLayout(top)

        self.model = ChannelModel()
        self.view = QtWidgets.QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.verticalHeader().setVisible(False)
        self.view.verticalHeader().setDefaultSectionSize(22)
        self.view.setShowGrid(False)
        hh = self.view.horizontalHeader()
        hh.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.view.setColumnWidth(1, 150)
        self.view.setColumnWidth(2, 90)
        root.addWidget(self.view, 1)

        self.search.textChanged.connect(self._on_filter)

    def _on_filter(self, text):
        self.model.set_filter(text)
        self._update_count()

    def _update_count(self):
        total = len(self._raw)
        vis = self.model.visible()
        self.count.setText(f"{vis}/{total} каналов" if vis != total else f"{total} каналов")

    def update_frame(self, f):
        if getattr(f, "raw", None):
            self._raw = f.raw
        if getattr(f, "raw_units", None):
            self._units.update(f.raw_units)
        self.model.set_values(self._raw, self._units)
        self._update_count()
