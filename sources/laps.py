"""Lap store — records completed laps and aligns them on a distance axis.

This powers the i2-style lap comparison worksheet: every finished lap is
resampled onto a uniform lap-distance grid (time-at-distance + the main
driving channels), so laps can be overlaid and a delta-time ("variance")
trace computed against a reference lap. Also provides the *live* delta of
the lap currently being driven vs the session-best lap.

Pure numpy, no Qt — safe to unit-test headless.
"""
from __future__ import annotations

import numpy as np


class LapRec:
    """One completed lap resampled onto a uniform distance grid."""
    __slots__ = ("lap", "time_s", "dist", "t_at_d", "speed", "thr", "brk", "steer")

    def __init__(self, lap, time_s, dist, t_at_d, speed, thr, brk, steer):
        self.lap = lap
        self.time_s = time_s
        self.dist = dist          # m, uniform grid from 0
        self.t_at_d = t_at_d      # s into the lap at each grid point
        self.speed = speed        # km/h
        self.thr = thr            # %
        self.brk = brk            # %
        self.steer = steer        # -1..1

    def delta_to(self, ref: "LapRec") -> np.ndarray:
        """Time lost(+)/gained(-) vs *ref* at each of this lap's grid points."""
        tref = np.interp(self.dist, ref.dist, ref.t_at_d)
        return self.t_at_d - tref


class LapStore:
    MAX_LAPS = 40
    MIN_SAMPLES = 40
    MIN_LAP_S = 20.0
    MAX_LAP_S = 45 * 60.0

    def __init__(self):
        self.laps: list[LapRec] = []
        self.best: LapRec | None = None
        self.version = 0            # bumped whenever self.laps changes
        self._track = ""
        self._cur_lap_no: int | None = None
        self._wall0 = 0.0           # wall-clock at current lap start
        self._buf: list[tuple] = [] # (dist, t, speed, thr%, brk%, steer)
        self._tlen = 0.0            # best estimate of track length (m)

    # ------------------------------------------------------------------
    def push(self, f) -> None:
        """Feed every rendered frame; lap boundaries are detected here."""
        if not f.connected:
            return
        # new track / session -> start over
        if f.track and f.track != self._track:
            self._track = f.track
            self.laps.clear()
            self.best = None
            self._buf = []
            self._cur_lap_no = None
            self._tlen = 0.0
            self.version += 1

        lapno = int(f.lap)
        if self._cur_lap_no is None:
            self._cur_lap_no = lapno
            self._wall0 = f.t
            self._buf = []
        elif lapno != self._cur_lap_no:
            self._finalise(self._cur_lap_no, f.last_lap)
            self._cur_lap_no = lapno
            self._wall0 = f.t
            self._buf = []

        d = float(f.lap_dist)
        if d < 0:
            return
        t = float(f.cur_lap_time) if f.cur_lap_time > 0 else (f.t - self._wall0)
        # skip stalled/duplicate samples (paused, garage)
        if self._buf and t <= self._buf[-1][1] and d <= self._buf[-1][0]:
            return
        self._buf.append((d, t, f.speed, f.throttle * 100.0,
                          f.brake * 100.0, f.steer))

    # ------------------------------------------------------------------
    def _finalise(self, lapno: int, last_lap_time: float) -> None:
        buf = self._buf
        if len(buf) < self.MIN_SAMPLES:
            return
        arr = np.asarray(buf, dtype=np.float64)
        d, t = arr[:, 0], arr[:, 1]

        # keep strictly-increasing distance (drops resets/tows/reverse)
        prev_max = np.maximum.accumulate(np.concatenate(([-1e9], d[:-1])))
        keep = d > prev_max
        arr = arr[keep]
        if len(arr) < self.MIN_SAMPLES:
            return
        d, t = arr[:, 0], arr[:, 1]
        # time must be increasing too
        prev_t = np.maximum.accumulate(np.concatenate(([-1e9], t[:-1])))
        arr = arr[t > prev_t]
        if len(arr) < self.MIN_SAMPLES:
            return
        d, t = arr[:, 0], arr[:, 1]

        self._tlen = max(self._tlen, float(d[-1]))
        # completeness: must start near the line and cover most of the track
        if d[0] > 0.10 * self._tlen or d[-1] < 0.90 * self._tlen:
            return

        # official lap time when plausible, else the sampled duration
        dur = float(t[-1] - t[0])
        lap_time = dur
        if last_lap_time and self.MIN_LAP_S < last_lap_time < self.MAX_LAP_S \
                and abs(last_lap_time - dur) < max(5.0, dur * 0.25):
            lap_time = float(last_lap_time)
        if not (self.MIN_LAP_S < lap_time < self.MAX_LAP_S):
            return

        # resample onto a uniform grid
        step = max(2.0, float(d[-1]) / 2000.0)
        grid = np.arange(0.0, float(d[-1]), step)
        if len(grid) < 20:
            return
        t0 = t - t[0]
        rec = LapRec(
            lap=lapno,
            time_s=lap_time,
            dist=grid,
            t_at_d=np.interp(grid, d, t0),
            speed=np.interp(grid, d, arr[:, 2]),
            thr=np.interp(grid, d, arr[:, 3]),
            brk=np.interp(grid, d, arr[:, 4]),
            steer=np.interp(grid, d, arr[:, 5]),
        )
        self.laps.append(rec)
        if self.best is None or rec.time_s < self.best.time_s:
            self.best = rec
        # cap history, never dropping the best lap
        while len(self.laps) > self.MAX_LAPS:
            for i, r in enumerate(self.laps):
                if r is not self.best:
                    self.laps.pop(i)
                    break
            else:
                break
        self.version += 1

    # ------------------------------------------------------------------
    def live_delta(self, f) -> float | None:
        """Delta of the in-progress lap vs the best lap at the car's current
        lap distance. Positive = slower than best. None when unavailable."""
        ref = self.best
        if ref is None or f.lap_dist <= 0 or f.lap_dist > ref.dist[-1]:
            return None
        t = float(f.cur_lap_time) if f.cur_lap_time > 0 else (f.t - self._wall0)
        if t <= 0:
            return None
        dd = t - float(np.interp(f.lap_dist, ref.dist, ref.t_at_d))
        if abs(dd) > 30.0:      # out-lap / tow / nonsense
            return None
        return dd

    def current_arrays(self):
        """(dist, t, speed, thr, brk, steer) of the lap being driven now."""
        if len(self._buf) < 2:
            return None
        arr = np.asarray(self._buf, dtype=np.float64)
        return arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4], arr[:, 5]
