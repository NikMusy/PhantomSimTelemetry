"""iRacing telemetry source.

Reads iRacing's live shared memory (``Local\\IRSDKMemMapFileName``, ~60 Hz) and
maps it onto the common :class:`Frame`. Pure reader — only attaches to the
existing mapping, never creates one, so it can't disturb the sim.

The wire layout (irsdk header + per-variable headers + double-buffered data)
matches the public iRacing SDK and was validated against real .ibt captures.

Optionally re-broadcasts the normalised frame over TCP (``share_port``) so a
strategist on the Radmin network can open the same UI live.
"""
from __future__ import annotations

import ctypes
import re
import time
from ctypes import wintypes
from typing import Optional

from .base import Frame, SourceBase
from .net_frame import FrameServer

MEMMAP_NAME = "Local\\IRSDKMemMapFileName"
FILE_MAP_READ = 0x0004
IRSDK_ST_CONNECTED = 1
MAX_BUFS = 4
MAX_STRING = 32
MAX_DESC = 64
VARHEADER_SIZE = 16 + MAX_STRING + MAX_DESC + MAX_STRING  # = 144

# irsdk_VarType -> ctypes
_CT = {
    0: ctypes.c_char,    # char
    1: ctypes.c_bool,    # bool
    2: ctypes.c_int,     # int
    3: ctypes.c_int,     # bitField
    4: ctypes.c_float,   # float
    5: ctypes.c_double,  # double
}
# irsdk_VarType -> element size in bytes
_SIZE = {0: 1, 1: 1, 2: 4, 3: 4, 4: 4, 5: 8}


class _VarBuf(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("tickCount", ctypes.c_int), ("bufOffset", ctypes.c_int),
                ("pad", ctypes.c_int * 2)]


class _Header(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("ver", ctypes.c_int), ("status", ctypes.c_int), ("tickRate", ctypes.c_int),
        ("sessionInfoUpdate", ctypes.c_int), ("sessionInfoLen", ctypes.c_int),
        ("sessionInfoOffset", ctypes.c_int), ("numVars", ctypes.c_int),
        ("varHeaderOffset", ctypes.c_int), ("numBuf", ctypes.c_int),
        ("bufLen", ctypes.c_int), ("pad1", ctypes.c_int * 2),
        ("varBuf", _VarBuf * MAX_BUFS),
    ]


class _VarHeader(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("type", ctypes.c_int), ("offset", ctypes.c_int), ("count", ctypes.c_int),
        ("countAsTime", ctypes.c_char), ("pad", ctypes.c_char * 3),
        ("name", ctypes.c_char * MAX_STRING),
        ("desc", ctypes.c_char * MAX_DESC),
        ("unit", ctypes.c_char * MAX_STRING),
    ]


def _section_handle():
    k = ctypes.windll.kernel32
    k.OpenFileMappingW.restype = wintypes.HANDLE
    k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    return k.OpenFileMappingW(FILE_MAP_READ, False, MEMMAP_NAME)


class IRacingSource(SourceBase):
    name = "iRacing"

    def __init__(self, share_port: Optional[int] = None):
        self._base = None            # mapped view address (int)
        self._handle = None
        self._vars: dict[str, tuple[int, int]] = {}   # name -> (type, offset)
        self._raw_layout: list[tuple[str, int, int]] = []   # (display, type, offset)
        self._units: dict[str, str] = {}                    # display -> unit
        self._nvars = 0
        self._last_tick = -1
        self._last_change = 0.0
        # cached session-string fields
        self._sess_update = -1
        self._track_name = ""
        self._session_name = ""
        self._redline = 0.0
        self._fuel_cap = 0.0
        self.last_error = ""
        # optional re-broadcast for a remote strategist
        self._server = FrameServer(self.poll, share_port) if share_port else None

    # ---- discovery ---------------------------------------------------
    @staticmethod
    def available() -> bool:
        h = _section_handle()
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False

    # ---- lifecycle ---------------------------------------------------
    def start(self):
        self._attach()
        if self._server:
            self._server.start()

    def stop(self):
        if self._server:
            self._server.stop()
        self._detach()

    def _attach(self) -> bool:
        if self._base:
            return True
        h = _section_handle()
        if not h:
            return False
        k = ctypes.windll.kernel32
        k.MapViewOfFile.restype = wintypes.LPVOID
        k.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                    wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        base = k.MapViewOfFile(h, FILE_MAP_READ, 0, 0, 0)
        if not base:
            k.CloseHandle(h)
            return False
        self._handle = h
        self._base = int(base)
        self._vars = {}
        self._nvars = 0
        return True

    def _detach(self):
        try:
            if self._base:
                ctypes.windll.kernel32.UnmapViewOfFile(ctypes.c_void_p(self._base))
            if self._handle:
                ctypes.windll.kernel32.CloseHandle(self._handle)
        except Exception:
            pass
        self._base = None
        self._handle = None
        self._vars = {}

    # ---- header helpers ----------------------------------------------
    def _header(self) -> Optional[_Header]:
        if not self._base:
            return None
        try:
            return _Header.from_address(self._base)
        except Exception:
            return None

    def _build_var_map(self, hdr: _Header):
        vars_ = {}
        layout = []
        units = {}
        vho = self._base + hdr.varHeaderOffset
        for i in range(hdr.numVars):
            vh = _VarHeader.from_address(vho + i * VARHEADER_SIZE)
            try:
                nm = vh.name.decode("ascii", "ignore").rstrip("\x00")
            except Exception:
                continue
            if not nm:
                continue
            vtype, base_off, count = vh.type, vh.offset, vh.count
            try:
                unit = vh.unit.decode("ascii", "ignore").rstrip("\x00")
            except Exception:
                unit = ""
            vars_[nm] = (vtype, base_off)            # scalar (first element) lookup
            esz = _SIZE.get(vtype, 4)
            if count <= 1:
                layout.append((nm, vtype, base_off)); units[nm] = unit
            else:
                for c in range(count):
                    dn = "%s[%d]" % (nm, c)
                    layout.append((dn, vtype, base_off + c * esz)); units[dn] = unit
        self._vars = vars_
        self._raw_layout = layout
        self._units = units
        self._nvars = hdr.numVars

    def _read_at(self, buf_off: int, vtype: int, off: int) -> float:
        ct = _CT.get(vtype)
        if ct is None:
            return 0.0
        try:
            addr = self._base + buf_off + off
            if vtype == 0:
                return float(ord(ct.from_address(addr).value or b"\x00"))
            return float(ct.from_address(addr).value)
        except Exception:
            return 0.0

    def _latest_buf(self, hdr: _Header) -> tuple[int, int]:
        best, best_tick = 0, -1
        for i in range(min(hdr.numBuf, MAX_BUFS)):
            t = hdr.varBuf[i].tickCount
            if t > best_tick:
                best_tick, best = t, i
        return hdr.varBuf[best].bufOffset, best_tick

    def _val(self, buf_off: int, name: str, default=0.0):
        v = self._vars.get(name)
        if v is None:
            return default
        vtype, offset = v
        ct = _CT.get(vtype)
        if ct is None:
            return default
        try:
            addr = self._base + buf_off + offset
            if vtype == 0:      # char
                return float(ord(ct.from_address(addr).value or b"\x00"))
            return float(ct.from_address(addr).value)
        except Exception:
            return default

    def _ival(self, buf_off: int, name: str, default=0) -> int:
        return int(self._val(buf_off, name, default))

    # ---- session string (parsed rarely) ------------------------------
    def _parse_session(self, hdr: _Header):
        if hdr.sessionInfoUpdate == self._sess_update:
            return
        try:
            raw = ctypes.string_at(self._base + hdr.sessionInfoOffset,
                                   max(0, hdr.sessionInfoLen))
            txt = raw.decode("latin-1", "ignore")
        except Exception:
            return
        self._sess_update = hdr.sessionInfoUpdate
        m = re.search(r"TrackDisplayName:\s*(.+)", txt)
        if m:
            self._track_name = m.group(1).strip()
        m = re.search(r"DriverCarRedLine:\s*([\d.]+)", txt)
        if m:
            try:
                self._redline = float(m.group(1))
            except Exception:
                pass
        m = re.search(r"DriverCarFuelMaxLtr:\s*([\d.]+)", txt)
        if m:
            try:
                self._fuel_cap = float(m.group(1))
            except Exception:
                pass

    # ---- main poll ---------------------------------------------------
    def is_live(self) -> bool:
        return (time.monotonic() - self._last_change) < 1.5

    def poll(self) -> Frame:
        now = time.monotonic()
        f = Frame(t=now, game="iRacing")
        if not self._attach():
            return f
        hdr = self._header()
        if hdr is None:
            self._detach()
            return f
        if not (hdr.status & IRSDK_ST_CONNECTED) or hdr.numVars <= 0:
            return f
        if self._nvars != hdr.numVars or not self._vars:
            self._build_var_map(hdr)
        self._parse_session(hdr)

        # latest buffer with a torn-read guard
        buf_off, tick = self._latest_buf(hdr)
        for _ in range(3):
            buf_off2, tick2 = self._latest_buf(self._header())
            if tick2 == tick:
                break
            buf_off, tick = buf_off2, tick2

        # --- inputs / engine ---
        f.speed = self._val(buf_off, "Speed") * 3.6
        f.rpm = self._val(buf_off, "RPM")
        f.max_rpm = self._redline
        f.gear = self._ival(buf_off, "Gear")
        f.throttle = _c01(self._val(buf_off, "Throttle"))
        f.brake = _c01(self._val(buf_off, "Brake"))
        f.clutch = _c01(self._val(buf_off, "Clutch"))
        ang = self._val(buf_off, "SteeringWheelAngle")
        amax = self._val(buf_off, "SteeringWheelAngleMax")
        f.steer = max(-1.0, min(1.0, ang / amax)) if amax > 0.1 else max(-1.0, min(1.0, ang / 5.0))
        drs = self._ival(buf_off, "DRS_Status", 0)
        f.drs = 1 if drs >= 1 else 0

        # --- fluids / temps ---
        f.fuel = self._val(buf_off, "FuelLevel")
        f.fuel_capacity = self._fuel_cap
        f.water_temp = self._val(buf_off, "WaterTemp")
        f.oil_temp = self._val(buf_off, "OilTemp")

        # --- tyres (FL, FR, RL, RR) ---
        for i, pfx in enumerate(("LF", "RF", "LR", "RR")):
            f.tyre_temp[i] = self._val(buf_off, pfx + "tempCM")
            f.tyre_life[i] = _c01(self._val(buf_off, pfx + "wearM", 1.0)) * 100.0
            p = self._val(buf_off, pfx + "pressure", 0.0)   # kPa if present
            f.tyre_press[i] = p * 0.1450377 if p else 0.0

        # --- timing ---
        f.lap = self._ival(buf_off, "Lap")
        f.lap_dist = self._val(buf_off, "LapDist")
        pct = self._val(buf_off, "LapDistPct")
        f.track_len = (f.lap_dist / pct) if pct > 0.01 else f.track_len
        f.last_lap = max(0.0, self._val(buf_off, "LapLastLapTime"))
        f.best_lap = max(0.0, self._val(buf_off, "LapBestLapTime"))
        f.cur_lap_time = max(0.0, self._val(buf_off, "LapCurrentLapTime"))
        f.position = self._ival(buf_off, "PlayerCarPosition")

        # --- track map: GPS lat/lon as relative XY ---
        f.pos_x = self._val(buf_off, "Lon")
        f.pos_y = self._val(buf_off, "Lat")

        # --- vehicle dynamics ---
        G = 9.80665
        f.g_lat = self._val(buf_off, "LatAccel") / G
        f.g_long = self._val(buf_off, "LongAccel") / G
        f.g_vert = self._val(buf_off, "VertAccel") / G
        f.yaw_rate = self._val(buf_off, "YawRate") * 57.29578
        f.pitch = self._val(buf_off, "Pitch") * 57.29578
        f.roll = self._val(buf_off, "Roll") * 57.29578
        f.steer_torque = self._val(buf_off, "SteeringWheelTorque")

        # --- aids / setup ---
        f.brake_bias = self._val(buf_off, "dcBrakeBias")
        f.abs_active = 1 if self._val(buf_off, "BrakeABSactive") >= 0.5 else 0
        f.tc_level = self._val(buf_off, "dcTractionControl")
        f.on_pit_road = 1 if self._val(buf_off, "OnPitRoad") >= 0.5 else 0

        # --- engine / fluids extras ---
        f.oil_press = self._val(buf_off, "OilPress")
        f.fuel_press = self._val(buf_off, "FuelPress")
        f.manifold_press = self._val(buf_off, "ManifoldPress")
        f.voltage = self._val(buf_off, "Voltage")
        f.fuel_per_hour = self._val(buf_off, "FuelUsePerHour")
        f.fuel_pct = self._val(buf_off, "FuelLevelPct")
        f.delta_best = self._val(buf_off, "LapDeltaToBestLap")

        # --- environment ---
        f.track_temp = self._val(buf_off, "TrackTempCrew")
        f.air_temp = self._val(buf_off, "AirTemp")
        f.wind_vel = self._val(buf_off, "WindVel")
        f.incidents = self._ival(buf_off, "PlayerCarMyIncidentCount")

        # --- per-corner extras (FL, FR, RL, RR) ---
        for i, pfx in enumerate(("LF", "RF", "LR", "RR")):
            f.tyre_temp_in[i] = self._val(buf_off, pfx + "tempCL")
            f.tyre_temp_out[i] = self._val(buf_off, pfx + "tempCR")
            f.ride_height[i] = self._val(buf_off, pfx + "rideHeight") * 1000.0
            f.susp_pos[i] = self._val(buf_off, pfx + "shockDefl") * 1000.0

        f.drs = 1 if self._ival(buf_off, "DRS_Status", 0) >= 1 else 0

        f.track = self._track_name
        f.session = self._session_name or "Session"

        # full channel dump (every iRacing variable, arrays expanded)
        raw = {}
        for dn, vtype, off in self._raw_layout:
            raw[dn] = self._read_at(buf_off, vtype, off)
        f.raw = raw
        f.raw_units = self._units  # reference (free locally; throttled on the wire)

        # liveness from advancing tick
        if tick != self._last_tick:
            self._last_tick = tick
            self._last_change = now
        f.connected = self.is_live()
        return f


def _c01(x: float) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return 0.0 if x < 0 else (1.0 if x > 1 else x)
