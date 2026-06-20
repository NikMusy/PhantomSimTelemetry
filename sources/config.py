"""Tiny JSON settings store (remembers the last LMU IP/port and F1 port).

Saved next to the executable when frozen, otherwise in the project folder, so
the .exe keeps your Radmin connection details between runs.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULTS = {
    "lmu_host": "127.0.0.1",
    "lmu_port": 8000,
    "lmu_local": False,        # True -> read this PC's shared memory instead
    "f1_port": 20777,
    "f1_host": "127.0.0.1",
    "f1_local": True,          # True -> listen to the game on this PC
    "f1_share": True,          # when local, re-broadcast to a strategist
    "f1_link_port": 8100,      # TCP bridge port (share / connect)
    "iracing_host": "127.0.0.1",
    "iracing_port": 8100,
    "iracing_local": True,     # True -> read this PC's iRacing shared memory
    "iracing_share": True,     # when local, re-broadcast to a strategist
    "last_game": "LMU",
}


def _config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "settings.json"


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        p = _config_path()
        if p.exists():
            cfg.update(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        pass
    return cfg


def save(cfg: dict) -> None:
    try:
        merged = dict(DEFAULTS)
        merged.update(cfg)
        _config_path().write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
