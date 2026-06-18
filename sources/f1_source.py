"""F1 25 telemetry source.

Wraps the bundled ``f1_telemetry`` package: a background UDP listener feeds a
``TelemetryStore`` (on the GUI thread via a queued Qt signal) and ``poll()``
samples that store into the common :class:`Frame`.

F1 UDP arrays are ordered  RL, RR, FL, FR — they are reordered here to the
project-wide  FL, FR, RL, RR.
"""
from __future__ import annotations

import time

from .base import Frame, SourceBase
from .f1_telemetry.listener import UdpListener
from .f1_telemetry.store import TelemetryStore

# F1 wheel order RL,RR,FL,FR  ->  our FL,FR,RL,RR
_WHEEL = [2, 3, 0, 1]


def _reorder(seq):
    try:
        return [float(seq[i]) for i in _WHEEL]
    except Exception:
        return [0.0, 0.0, 0.0, 0.0]


class F1Source(SourceBase):
    name = "F1 25"

    def __init__(self, port: int = 20777):
        self.port = port
        self.store = TelemetryStore()
        self.listener = UdpListener(port=port)
        self.listener.packet.connect(self._on_packet)
        self._track_len_est = 0.0
        self._started = False

    # --- listener plumbing -------------------------------------------
    def _on_packet(self, pid, obj, header):
        self.store.update(pid, obj, header)

    def start(self):
        if not self._started:
            self.listener.start()
            self._started = True

    def stop(self):
        try:
            self.listener.stop()
        except Exception:
            pass
        self._started = False

    def is_live(self) -> bool:
        return self.store.is_live()

    # --- sampling -----------------------------------------------------
    def poll(self) -> Frame:
        s = self.store
        f = Frame(t=time.monotonic(), game="F1 25")
        f.connected = s.is_live()

        f.track = s.track_name()
        f.session = _SESSION.get(s.session_type, "Session")
        f.num_cars = s.num_active

        f.speed = float(s.speed)
        f.rpm = float(s.rpm)
        f.max_rpm = float(s.max_rpm or 13000)
        f.gear = int(s.gear)
        f.throttle = _c01(s.throttle)
        f.brake = _c01(s.brake)
        f.clutch = _c01(s.clutch / 100.0 if s.clutch > 1 else s.clutch)
        f.steer = max(-1.0, min(1.0, float(s.steer)))
        f.drs = int(s.drs)
        f.ers_pct = s.ers_pct()

        f.fuel = float(s.fuel_in_tank)
        f.fuel_capacity = float(s.fuel_capacity or 110.0)
        f.water_temp = float(s.engine_temp)
        f.oil_temp = 0.0

        f.tyre_temp = _reorder(s.tyre_inner_temp)
        f.tyre_press = _reorder(s.tyre_pressure)
        f.brake_temp = _reorder(s.brake_temps)
        wear = _reorder(s.tyre_wear)            # % worn
        f.tyre_life = [max(0.0, 100.0 - w) for w in wear]

        f.lap = int(s.current_lap)
        f.total_laps = int(s.total_laps)
        f.lap_dist = float(s.lap_distance)
        if s.lap_distance > self._track_len_est:
            self._track_len_est = float(s.lap_distance)
        f.track_len = self._track_len_est
        f.last_lap = s.last_lap_ms / 1000.0 if s.last_lap_ms else 0.0
        f.best_lap = s.best_lap_ms / 1000.0 if s.best_lap_ms else 0.0
        f.cur_lap_time = s.current_lap_ms / 1000.0 if s.current_lap_ms else 0.0
        f.sector = int(s.sector)
        f.position = int(s.position)

        idx = s.player_idx
        if 0 <= idx < len(s.car_xy):
            f.pos_x, f.pos_y = s.car_xy[idx]

        return f


_SESSION = {
    0: "Unknown", 1: "Practice 1", 2: "Practice 2", 3: "Practice 3",
    4: "Short P", 5: "Q1", 6: "Q2", 7: "Q3", 8: "Short Q", 9: "OSQ",
    10: "Race", 11: "Race 2", 12: "Race 3", 13: "Time Trial",
    15: "Race", 16: "Race", 17: "Race",
}


def _c01(x) -> float:
    x = float(x)
    return 0.0 if x < 0 else (1.0 if x > 1 else x)
