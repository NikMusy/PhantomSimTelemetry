"""Classic MoTeC i2 Pro look: grey Windows chrome around pure-black plot
areas, thin saturated traces (red / yellow / green / cyan / magenta), white
list panes with black text, small Tahoma fonts, square corners everywhere."""

# ---- application chrome (the grey i2 shell) -------------------------------
CHROME = "#d4d0c8"          # classic window grey
CHROME_LT = "#e6e2da"       # hovered / raised
CHROME_DK = "#b8b4ac"       # pressed
CHROME_SH = "#808080"       # bevel shadow / borders
TEXT = "#000000"            # text on chrome
TEXT_DIM = "#404040"
LIST_BG = "#ffffff"         # white list panes (values, laps, channels)
ACCENT_CHROME = "#000080"   # classic navy selection / highlights on grey

# ---- plot surfaces (the black i2 graph area) ------------------------------
BG = "#000000"
PANEL = "#000000"
PANEL_HI = "#101010"
GRID = "#3a3a3a"
BORDER = "#808080"

# text on black surfaces
FG = "#ffffff"
FG_DIM = "#c0c0c0"
FG_FAINT = "#7a7a7a"

# ---- i2 trace palette (thin, saturated, on black) -------------------------
SPEED = "#ff3232"           # ground speed — classic i2 red
THROTTLE = "#00dc00"        # green
BRAKE = "#ff2020"           # red (separate strip from speed, as in i2)
GEAR = "#ff50ff"            # magenta
RPM = "#ffff00"             # yellow
STEER = "#00ffff"           # cyan
DELTA_POS = "#ff5050"       # losing time
DELTA_NEG = "#00dc00"       # gaining time

# accent on BLACK surfaces (live lap, peak readouts)
ACCENT = "#00ffff"

# tyre temp gradient stops (C) — drawn on black tyre blocks
TYRE_COLD = "#2f6bff"
TYRE_OK = "#00dc00"
TYRE_HOT = "#ffb02e"
TYRE_CRIT = "#ff3232"

QSS = f"""
QMainWindow, QDialog {{
    background: {CHROME};
}}
QWidget {{
    background: transparent;
    color: {TEXT};
    font-family: 'Tahoma', 'MS Shell Dlg 2', sans-serif;
    font-size: 11px;
}}
QLabel {{ background: transparent; }}
QFrame#panel, QWidget#panel {{
    background: {PANEL};
    border: 1px solid {CHROME_SH};
    border-radius: 0;
}}
QLabel#h {{ color: {FG_DIM}; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
QLabel#title {{ color: {FG}; font-size: 12px; font-weight: 700; letter-spacing: 1px; }}

QMenuBar {{
    background: {CHROME};
    color: {TEXT};
    border-bottom: 1px solid {CHROME_SH};
    font-size: 12px;
}}
QMenuBar::item {{ background: transparent; padding: 3px 9px; }}
QMenuBar::item:selected {{ background: {ACCENT_CHROME}; color: #ffffff; }}
QMenu {{
    background: #f6f4ee;
    color: {TEXT};
    border: 1px solid {CHROME_SH};
    font-size: 12px;
}}
QMenu::item {{ padding: 3px 24px 3px 20px; }}
QMenu::item:selected {{ background: {ACCENT_CHROME}; color: #ffffff; }}
QMenu::item:disabled {{ color: #9a9a9a; }}
QMenu::separator {{ height: 1px; background: {CHROME_SH}; margin: 3px 6px; }}

QToolBar {{
    background: {CHROME};
    border-bottom: 1px solid {CHROME_SH};
    spacing: 2px;
    padding: 1px 4px;
}}
QToolButton {{
    background: {CHROME};
    color: {TEXT};
    border: 1px solid transparent;
    padding: 2px 8px;
    font-size: 11px;
}}
QToolButton:hover {{ background: {CHROME_LT}; border: 1px solid {CHROME_SH}; }}
QToolButton:pressed, QToolButton:checked {{
    background: {CHROME_DK}; border: 1px solid {CHROME_SH};
}}

QStatusBar {{
    background: {CHROME};
    color: {TEXT};
    border-top: 1px solid #ffffff;
    font-size: 11px;
}}
QStatusBar QLabel {{ color: {TEXT}; padding: 0 6px; }}
QStatusBar::item {{ border: none; }}

QTabWidget::pane {{ border: 1px solid {CHROME_SH}; background: {CHROME}; }}
QTabBar::tab {{
    background: {CHROME_DK};
    color: {TEXT};
    padding: 3px 16px;
    border: 1px solid {CHROME_SH};
    font-size: 11px;
}}
QTabBar::tab:selected {{ background: #ffffff; font-weight: 700; }}
QTabBar::tab:!selected:hover {{ background: {CHROME_LT}; }}

QTableWidget, QTableView {{
    background: {LIST_BG};
    color: {TEXT};
    gridline-color: #d8d8d4;
    alternate-background-color: #f2f2ee;
    selection-background-color: {ACCENT_CHROME};
    selection-color: #ffffff;
    border: 1px solid {CHROME_SH};
    font-size: 12px;
}}
QHeaderView::section {{
    background: {CHROME};
    color: {TEXT};
    border: 1px solid {CHROME_SH};
    border-left: none; border-top: none;
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 700;
}}
QTableCornerButton::section {{ background: {CHROME}; border: 1px solid {CHROME_SH}; }}

QLineEdit {{
    background: {LIST_BG};
    color: {TEXT};
    border: 1px solid {CHROME_SH};
    border-radius: 0;
    padding: 2px 6px;
    selection-background-color: {ACCENT_CHROME};
    selection-color: #ffffff;
}}
QLineEdit:disabled {{ background: {CHROME_LT}; color: #9a9a9a; }}
QCheckBox {{ color: {TEXT}; font-size: 12px; }}
QPushButton {{
    background: {CHROME};
    color: {TEXT};
    border: 1px solid {CHROME_SH};
    border-radius: 0;
    padding: 4px 16px;
    font-size: 12px;
}}
QPushButton:hover {{ background: {CHROME_LT}; }}
QPushButton:pressed {{ background: {CHROME_DK}; }}

QScrollBar:vertical {{
    background: {CHROME}; width: 15px; border: 1px solid {CHROME_SH};
}}
QScrollBar::handle:vertical {{
    background: {CHROME_DK}; border: 1px solid {CHROME_SH}; min-height: 24px;
}}
QScrollBar:horizontal {{
    background: {CHROME}; height: 15px; border: 1px solid {CHROME_SH};
}}
QScrollBar::handle:horizontal {{
    background: {CHROME_DK}; border: 1px solid {CHROME_SH}; min-width: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ background: {CHROME}; border: 1px solid {CHROME_SH}; }}

QToolTip {{ background: #ffffe1; color: {TEXT}; border: 1px solid #000000; font-size: 11px; }}
"""


def tyre_color(temp_c: float) -> str:
    """Blue (cold) -> green (ideal ~85) -> orange -> red (>110)."""
    t = temp_c
    if t <= 50:
        return TYRE_COLD
    if t <= 80:
        return _lerp(TYRE_COLD, TYRE_OK, (t - 50) / 30.0)
    if t <= 95:
        return TYRE_OK
    if t <= 110:
        return _lerp(TYRE_OK, TYRE_HOT, (t - 95) / 15.0)
    if t <= 125:
        return _lerp(TYRE_HOT, TYRE_CRIT, (t - 110) / 15.0)
    return TYRE_CRIT


def life_color(pct: float) -> str:
    if pct >= 60:
        return TYRE_OK
    if pct >= 30:
        return TYRE_HOT
    return TYRE_CRIT


def _lerp(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    a = _rgb(c1)
    b = _rgb(c2)
    r = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return f"#{r[0]:02x}{r[1]:02x}{r[2]:02x}"


def _rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
