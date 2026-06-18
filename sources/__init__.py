"""Telemetry sources and the manager that auto-selects the live game."""
from __future__ import annotations

import time

from .base import Frame
from .lmu_source import LMUSource
from .f1_source import F1Source


class SourceManager:
    """Runs both game sources at once and reports whichever is producing live
    data. LMU is read straight from shared memory each poll; F1 streams over UDP
    in the background. The active game is chosen automatically and only switched
    when the current one goes quiet, to avoid flapping."""

    def __init__(self, f1_port: int = 20777):
        self.lmu = LMUSource()
        self.f1 = F1Source(port=f1_port)
        self._active = None          # the source object currently shown
        self._last_frame = Frame()

    def start(self):
        self.lmu.start()
        self.f1.start()

    def stop(self):
        self.lmu.stop()
        self.f1.stop()

    def poll(self) -> Frame:
        lmu_live = self.lmu.is_live()
        f1_live = self.f1.is_live()

        # choose active source
        if self._active is self.lmu and lmu_live:
            pass
        elif self._active is self.f1 and f1_live:
            pass
        elif lmu_live:
            self._active = self.lmu
        elif f1_live:
            self._active = self.f1
        # else keep the previous active (so the last game's data lingers)

        if self._active is None:
            # nothing live yet — probe LMU shared memory so the user sees the
            # game name as soon as a session loads
            f = self.lmu.poll()
            self.f1.poll()  # keep store warm / detect first packet
            self._last_frame = f
            return f

        f = self._active.poll()
        self._last_frame = f
        return f

    def status(self) -> dict:
        return {
            "lmu": self.lmu.is_live(),
            "f1": self.f1.is_live(),
            "active": self._active.name if self._active else "—",
        }


class SingleManager:
    """Wraps one chosen source (from the start screen) behind the manager API
    the main window expects. Lights only the dot for the selected game."""

    def __init__(self, source, game: str):
        self.src = source
        self.game = game            # "LMU" | "F1 25"

    def start(self):
        self.src.start()

    def stop(self):
        self.src.stop()

    def poll(self) -> Frame:
        return self.src.poll()

    def status(self) -> dict:
        live = self.src.is_live()
        return {
            "lmu": live and self.game == "LMU",
            "f1": live and self.game == "F1 25",
            "active": self.game if live else "—",
            "error": getattr(self.src, "last_error", ""),
        }
