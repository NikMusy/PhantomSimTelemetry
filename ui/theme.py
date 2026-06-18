"""Dark, dense colour palette for the live telemetry worksheet."""

# base surfaces
BG = "#0a0c10"
PANEL = "#111620"
PANEL_HI = "#161c28"
GRID = "#1d2533"
BORDER = "#222b3a"

# text
FG = "#e6edf6"
FG_DIM = "#8593a8"
FG_FAINT = "#56627a"

# channel colours (MoTeC-ish bright on black)
SPEED = "#4fd1ff"
THROTTLE = "#3ad16a"
BRAKE = "#ff4d4d"
GEAR = "#ffd24a"
RPM = "#ff8c3b"
STEER = "#c08bff"
DELTA_POS = "#ff5d5d"
DELTA_NEG = "#37e07a"

# tyre temp gradient stops (C)
TYRE_COLD = "#2f6bff"
TYRE_OK = "#37e07a"
TYRE_HOT = "#ffb02e"
TYRE_CRIT = "#ff3b3b"

ACCENT = "#4fd1ff"

QSS = f"""
QWidget {{
    background: {BG};
    color: {FG};
    font-family: 'Segoe UI', 'Consolas', sans-serif;
    font-size: 12px;
}}
QFrame#panel, QWidget#panel {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QLabel#h {{ color: {FG_DIM}; font-size: 10px; font-weight: 600; letter-spacing: 1px; }}
QLabel#title {{ color: {FG}; font-size: 13px; font-weight: 700; letter-spacing: 1px; }}
QToolTip {{ background: {PANEL_HI}; color: {FG}; border: 1px solid {BORDER}; }}
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
