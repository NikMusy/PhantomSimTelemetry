"""Networked Le Mans Ultimate source.

Connects to an LMU Pit Wall telemetry server over WebSocket
(``ws://<host>:<port>/ws/lmu``) — the same JSON snapshot the web dashboard
consumes — and maps it onto the common :class:`Frame`. This is what powers the
"connect by Radmin IP + port" flow: the game runs on one PC, this app shows the
telemetry from anywhere on the Radmin network.

A background thread keeps the socket open and auto-reconnects; ``poll()`` just
converts the most recent snapshot.
"""
from __future__ import annotations

import json
import threading
import time

import websocket  # websocket-client

from .base import Frame, SourceBase

SESSION_NAMES = {
    0: "Test", 1: "Practice", 2: "Practice", 3: "Practice", 4: "Practice",
    5: "Qualify", 6: "Qualify", 7: "Qualify", 8: "Qualify",
    9: "Warmup", 10: "Race", 11: "Race", 12: "Race", 13: "Race", 14: "Race",
}
_KPA_TO_PSI = 0.1450377


class LMUNetSource(SourceBase):
    name = "LMU"

    def __init__(self, host: str, port: int = 8000, path: str = "/ws/lmu"):
        self.host = host.strip()
        self.port = int(port)
        self.path = path if path.startswith("/") else "/" + path
        self.url = f"ws://{self.host}:{self.port}{self.path}"

        self._snap = None
        self._snap_t = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.last_error = ""
        self.connected_ws = False

    # --- lifecycle ----------------------------------------------------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

    _ws = None

    def _run(self):
        while not self._stop.is_set():
            try:
                self._ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self._on_message,
                    on_open=self._on_open,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                self.last_error = str(exc)
            self.connected_ws = False
            if self._stop.is_set():
                break
            time.sleep(1.5)  # backoff before reconnect

    def _on_open(self, _ws):
        self.connected_ws = True
        self.last_error = ""

    def _on_error(self, _ws, err):
        self.last_error = str(err)

    def _on_close(self, _ws, *a):
        self.connected_ws = False

    def _on_message(self, _ws, msg):
        try:
            snap = json.loads(msg)
        except Exception:
            return
        with self._lock:
            self._snap = snap
            self._snap_t = time.monotonic()

    # --- sampling -----------------------------------------------------
    def is_live(self) -> bool:
        with self._lock:
            snap = self._snap
            age = time.monotonic() - self._snap_t
        return bool(snap) and snap.get("status") == "live" and age < 2.5

    def poll(self) -> Frame:
        with self._lock:
            snap = self._snap
            age = time.monotonic() - self._snap_t
        f = Frame(t=time.monotonic(), game="LMU")
        if not snap or snap.get("status") != "live" or age > 3.0:
            return f
        return _snap_to_frame(snap, f)


def _snap_to_frame(s: dict, f: Frame) -> Frame:
    sess = s.get("session") or {}
    timing = s.get("timing") or {}
    tires = s.get("tires") or {}

    f.connected = True
    f.track = s.get("track") or sess.get("track_name") or ""
    f.session = SESSION_NAMES.get(int(sess.get("session", -1)), "Session")
    f.num_cars = int(sess.get("num_vehicles", 0) or 0)

    f.speed = float(s.get("speed_kmh", 0) or 0)
    f.rpm = float(s.get("rpm", 0) or 0)
    f.max_rpm = float(s.get("max_rpm", 0) or 0)
    f.gear = int(s.get("gear", 0) or 0)
    f.throttle = _c01(s.get("throttle", 0))
    f.brake = _c01(s.get("brake", 0))
    f.clutch = _c01(s.get("clutch", 0))
    f.steer = max(-1.0, min(1.0, float(s.get("steering", 0) or 0)))
    f.drs = 1 if s.get("drs") else 0
    f.turbo = float(s.get("turbo_boost", 0) or 0)

    f.fuel = float(s.get("fuel", 0) or 0)
    f.fuel_capacity = float(s.get("fuel_capacity") or 0)
    f.water_temp = float(s.get("water_temp", 0) or 0)
    f.oil_temp = float(s.get("oil_temp", 0) or 0)

    for i, key in enumerate(("fl", "fr", "rl", "rr")):
        w = tires.get(key) or {}
        f.tyre_temp[i] = float(w.get("temp_center", w.get("temp_avg", 0)) or 0)
        f.tyre_press[i] = float(w.get("pressure", 0) or 0) * _KPA_TO_PSI
        f.tyre_life[i] = _c01(w.get("wear", 1)) * 100.0
        f.brake_temp[i] = float(w.get("brake_temp", 0) or 0)

    f.lap = int(s.get("lap_number", 0) or 0)
    f.total_laps = int(timing.get("total_laps", 0) or 0)
    f.track_len = float(sess.get("track_length", 0) or 0)
    f.last_lap = float(timing.get("last_lap") or 0)
    f.best_lap = float(timing.get("best_lap") or 0)
    f.cur_lap_time = float(timing.get("time_into_lap") or 0)
    f.sector = max(0, int(timing.get("current_sector", 1) or 1) - 1)
    f.position = int(timing.get("place", 0) or 0)

    # player position for the track map, from the field array
    for car in (s.get("field") or []):
        if car.get("is_player"):
            f.lap_dist = float(car.get("lap_dist", 0) or 0)
            f.pos_x = float(car.get("pos_x", 0) or 0)
            f.pos_y = float(car.get("pos_z", 0) or 0)
            break
    return f


def _c01(x) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return 0.0 if x < 0 else (1.0 if x > 1 else x)
