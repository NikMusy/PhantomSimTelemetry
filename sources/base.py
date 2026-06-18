"""Common normalised telemetry frame shared by every game source.

Each source (LMU shared memory, F1 25 UDP) maps its native data onto this one
struct so the UI never has to know which game is running. Units are unified:

    speed        km/h
    rpm          rev/min
    throttle     0..1
    brake        0..1
    clutch       0..1
    steer        -1..1   (left negative)
    fuel         litres
    temps        degrees Celsius
    tyre_press   psi
    tyre_life    0..100  (100 = fresh)
    lap times    seconds (0 = none)

Tyre / brake arrays are always ordered  FL, FR, RL, RR.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Frame:
    # --- meta ---------------------------------------------------------
    t: float = 0.0                 # monotonic timestamp of this sample
    connected: bool = False
    game: str = "—"               # "LMU" | "F1 25"
    track: str = ""
    session: str = ""

    # --- driver inputs / engine --------------------------------------
    speed: float = 0.0             # km/h
    rpm: float = 0.0
    max_rpm: float = 0.0
    gear: int = 0                  # -1 = R, 0 = N, 1..n
    throttle: float = 0.0          # 0..1
    brake: float = 0.0             # 0..1
    clutch: float = 0.0            # 0..1
    steer: float = 0.0             # -1..1

    # --- fluids / temps ----------------------------------------------
    fuel: float = 0.0              # litres
    fuel_capacity: float = 0.0
    water_temp: float = 0.0        # C
    oil_temp: float = 0.0          # C

    # --- tyres / brakes  (FL, FR, RL, RR) ----------------------------
    tyre_temp: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    tyre_press: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    tyre_life: List[float] = field(default_factory=lambda: [100.0, 100.0, 100.0, 100.0])
    brake_temp: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

    # --- lap / timing -------------------------------------------------
    lap: int = 0
    total_laps: int = 0
    lap_dist: float = 0.0          # metres into the lap
    track_len: float = 0.0         # metres
    last_lap: float = 0.0          # s
    best_lap: float = 0.0          # s
    cur_lap_time: float = 0.0      # s
    sector: int = 0                # 0..2
    position: int = 0
    num_cars: int = 0

    # --- track map ----------------------------------------------------
    pos_x: float = 0.0
    pos_y: float = 0.0

    # --- vehicle dynamics --------------------------------------------
    g_lat: float = 0.0             # lateral G (right +)
    g_long: float = 0.0            # longitudinal G (accel +, brake -)
    g_vert: float = 0.0            # vertical G
    yaw_rate: float = 0.0          # deg/s
    pitch: float = 0.0             # deg
    roll: float = 0.0              # deg
    steer_torque: float = 0.0      # Nm (steering shaft)

    # --- driver aids / setup -----------------------------------------
    brake_bias: float = 0.0        # % front
    abs_active: int = 0            # 0/1
    tc_active: int = 0             # 0/1
    tc_level: float = 0.0          # setting
    pit_limiter: int = 0
    on_pit_road: int = 0

    # --- engine / fluids extras --------------------------------------
    oil_press: float = 0.0         # bar
    fuel_press: float = 0.0        # bar
    manifold_press: float = 0.0    # bar/kPa
    voltage: float = 0.0           # V
    fuel_per_hour: float = 0.0     # L/h (or kg/h)
    fuel_pct: float = 0.0          # 0..1 tank
    delta_best: float = 0.0        # live delta to best lap (s)

    # --- environment --------------------------------------------------
    track_temp: float = 0.0        # C
    air_temp: float = 0.0          # C
    wind_vel: float = 0.0          # m/s
    incidents: int = 0

    # --- extra per-corner arrays  (FL, FR, RL, RR) -------------------
    tyre_temp_in: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    tyre_temp_out: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    ride_height: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])  # mm
    susp_pos: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])     # mm

    # --- game specific extras ----------------------------------------
    drs: int = 0                   # 1 = open / available flap
    ers_pct: float = 0.0           # F1 battery / iRacing P2P
    turbo: float = 0.0             # LMU boost (bar)

    # --- full raw channel dump (the complete iRacing channel list) ---
    raw: dict = field(default_factory=dict)        # name -> value (everything)
    raw_units: dict = field(default_factory=dict)  # name -> unit (sent occasionally)

    @property
    def lap_pct(self) -> float:
        if self.track_len > 0:
            return max(0.0, min(1.0, self.lap_dist / self.track_len))
        return 0.0

    @property
    def rpm_pct(self) -> float:
        if self.max_rpm > 0:
            return max(0.0, min(1.0, self.rpm / self.max_rpm))
        return 0.0


class SourceBase:
    """Interface every telemetry source implements."""

    name = "base"

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def poll(self) -> Frame:
        """Return the latest frame. Always returns a Frame; .connected tells
        the caller whether it carries live data."""
        raise NotImplementedError

    def is_live(self) -> bool:
        return False


def fmt_time(seconds: float) -> str:
    """Format a lap time in M:SS.mmm (or --:--.--- when missing)."""
    if not seconds or seconds <= 0:
        return "--:--.---"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:06.3f}"


def fmt_delta(seconds: float) -> str:
    if seconds is None:
        return "--.---"
    sign = "+" if seconds >= 0 else "-"
    return f"{sign}{abs(seconds):.3f}"
