"""Synthetic source for testing the UI without a game running.

Drives a fake car around an oval, generating plausible speed/throttle/brake/
gear/rpm/steer plus tyre and lap data so the whole worksheet can be verified
offline. Enable with ``main.py --demo``.
"""
from __future__ import annotations

import math
import time

from .base import Frame, SourceBase


class DemoSource(SourceBase):
    name = "DEMO"

    def __init__(self):
        self._t0 = time.monotonic()
        self._lap = 1
        self._best = 0.0
        self._last = 0.0
        self._lap_t0 = self._t0
        self.track_len = 4200.0

    def start(self): pass

    def stop(self): pass

    def is_live(self): return True

    def poll(self) -> Frame:
        now = time.monotonic()
        el = now - self._t0
        f = Frame(t=now, game="F1 25", connected=True)
        f.track = "DEMO CIRCUIT"
        f.session = "Race"
        f.num_cars = 20
        f.total_laps = 30

        # lap progress 0..1 over ~95s
        lap_dur = 95.0
        u = ((now - self._lap_t0) / lap_dur)
        if u >= 1.0:
            self._last = now - self._lap_t0
            if self._best == 0 or self._last < self._best:
                self._best = self._last
            self._lap += 1
            self._lap_t0 = now
            u = 0.0
        f.lap = self._lap
        f.cur_lap_time = now - self._lap_t0
        f.last_lap = self._last
        f.best_lap = self._best
        f.lap_dist = u * self.track_len
        f.track_len = self.track_len
        f.position = 4
        f.sector = min(2, int(u * 3))

        # cornering model: a few corners per lap
        corner = (math.sin(u * 2 * math.pi * 5) * 0.5 + 0.5)  # 0..1
        straight = 1.0 - corner
        f.speed = 90 + straight * 230 + math.sin(el * 0.7) * 4
        f.throttle = min(1.0, 0.25 + straight * 0.85)
        f.brake = max(0.0, corner - 0.55) * 1.8
        f.steer = math.sin(u * 2 * math.pi * 5) * corner
        f.gear = max(1, min(8, int(f.speed / 42) + 1))
        f.max_rpm = 13000
        f.rpm = 3000 + (f.speed % 42) / 42 * 9000 + f.throttle * 800
        f.clutch = 0.0
        f.drs = 1 if straight > 0.8 else 0
        f.ers_pct = 50 + 40 * math.sin(el * 0.2)

        f.fuel = max(0.0, 95 - el * 0.05)
        f.fuel_capacity = 110
        f.water_temp = 96 + 4 * math.sin(el * 0.1)
        f.oil_temp = 104 + 6 * math.sin(el * 0.08)

        base_t = 88 + corner * 18
        f.tyre_temp = [base_t + 6, base_t + 8, base_t + 2, base_t + 3]
        f.tyre_press = [23.2, 23.4, 21.8, 21.9]
        wear = min(60.0, el * 0.06)
        f.tyre_life = [100 - wear - 4, 100 - wear - 6, 100 - wear, 100 - wear - 2]
        f.brake_temp = [320 + corner * 260] * 4

        # --- dynamics / extras (synthetic but plausible) ---
        f.g_lat = f.steer * (corner * 3.0)
        f.g_long = f.throttle * 0.9 - f.brake * 2.6
        f.g_vert = 1.0 + math.sin(el * 3.0) * 0.15
        f.yaw_rate = f.steer * corner * 28.0
        f.pitch = -f.g_long * 1.4
        f.roll = f.g_lat * 1.1
        f.steer_torque = f.steer * 9.0 + math.sin(el * 4) * 0.5
        f.brake_bias = 56.5
        f.abs_active = 1 if f.brake > 0.85 else 0
        f.tc_active = 1 if (f.throttle > 0.9 and corner > 0.5) else 0
        f.tc_level = 3
        f.oil_press = 4.6 + f.rpm / 13000 * 1.4
        f.fuel_press = 3.0
        f.manifold_press = 0.9 + f.throttle * 1.3
        f.voltage = 13.8
        f.fuel_per_hour = 32 + f.throttle * 18
        f.fuel_pct = f.fuel / (f.fuel_capacity or 110)
        f.delta_best = math.sin(el * 0.3) * 0.4
        f.track_temp = 32 + 3 * math.sin(el * 0.05)
        f.air_temp = 24.0
        f.wind_vel = 3.2
        f.tyre_temp_in = [t + 5 for t in f.tyre_temp]
        f.tyre_temp_out = [t - 4 for t in f.tyre_temp]
        f.ride_height = [52, 52, 68, 68]
        f.susp_pos = [f.g_long * -3 + 18, f.g_long * -3 + 18,
                      f.g_long * 3 + 24, f.g_long * 3 + 24]

        # oval track map
        ang = u * 2 * math.pi
        f.pos_x = math.cos(ang) * 600 + math.sin(ang * 2) * 120
        f.pos_y = math.sin(ang) * 380

        # synthetic "full channel" dump for the All-Channels browser
        f.raw = {
            "SessionTime": el, "Speed": f.speed / 3.6, "RPM": f.rpm, "Gear": float(f.gear),
            "Throttle": f.throttle, "Brake": f.brake, "Clutch": f.clutch,
            "SteeringWheelAngle": f.steer * 5, "LapDist": f.lap_dist, "LapDistPct": u,
            "Lap": float(f.lap), "FuelLevel": f.fuel, "FuelLevelPct": f.fuel_pct,
            "WaterTemp": f.water_temp, "OilTemp": f.oil_temp, "OilPress": f.oil_press,
            "Voltage": f.voltage, "LatAccel": f.g_lat * 9.81, "LongAccel": f.g_long * 9.81,
            "VertAccel": f.g_vert * 9.81, "YawRate": f.yaw_rate / 57.3, "Pitch": f.pitch / 57.3,
            "Roll": f.roll / 57.3, "Lat": 50.33, "Lon": 6.95, "Brake_Bias": f.brake_bias,
            "PlayerCarPosition": float(f.position), "TrackTempCrew": f.track_temp,
            "AirTemp": f.air_temp, "WindVel": f.wind_vel,
        }
        f.raw_units = {
            "SessionTime": "s", "Speed": "m/s", "RPM": "rpm", "Throttle": "%", "Brake": "%",
            "Clutch": "%", "SteeringWheelAngle": "rad", "LapDist": "m", "LapDistPct": "%",
            "FuelLevel": "L", "FuelLevelPct": "%", "WaterTemp": "C", "OilTemp": "C",
            "OilPress": "bar", "Voltage": "V", "LatAccel": "m/s^2", "LongAccel": "m/s^2",
            "VertAccel": "m/s^2", "YawRate": "rad/s", "Lat": "deg", "Lon": "deg",
            "Brake_Bias": "%", "TrackTempCrew": "C", "AirTemp": "C", "WindVel": "m/s",
        }
        return f
