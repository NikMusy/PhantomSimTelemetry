"""Le Mans Ultimate telemetry source.

Reads the Windows shared-memory sections published by the rFactor2 Shared
Memory Map Plugin (``$rFactor2SMMP_Telemetry$`` / ``$rFactor2SMMP_Scoring$``)
— LMU is built on the rF2 engine and ships the same plugin interface. The
structs below mirror the plugin layout (pragma pack(4)).

Pure reader: it only ever *attaches* to an existing section, never creates one,
so it cannot interfere with the game/plugin writing the data.
"""
from __future__ import annotations

import ctypes
import math
import mmap
import sys
import time
from typing import Optional

from .base import Frame, SourceBase

TELEMETRY_SHM = "$rFactor2SMMP_Telemetry$"
SCORING_SHM = "$rFactor2SMMP_Scoring$"
MAX_MAPPED_VEHICLES = 128
KELVIN = 273.15


# ============================================================
# ctypes structures  (rF2 SMMP plugin, pack(4))
# ============================================================
class rF2Vec3(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double), ("z", ctypes.c_double)]


class rF2Wheel(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mSuspensionDeflection", ctypes.c_double),
        ("mRideHeight", ctypes.c_double),
        ("mSuspForce", ctypes.c_double),
        ("mBrakeTemp", ctypes.c_double),                  # Kelvin
        ("mBrakePressure", ctypes.c_double),
        ("mRotation", ctypes.c_double),
        ("mLateralPatchVel", ctypes.c_double),
        ("mLongitudinalPatchVel", ctypes.c_double),
        ("mLateralGroundVel", ctypes.c_double),
        ("mLongitudinalGroundVel", ctypes.c_double),
        ("mCamber", ctypes.c_double),
        ("mLateralForce", ctypes.c_double),
        ("mLongitudinalForce", ctypes.c_double),
        ("mTireLoad", ctypes.c_double),
        ("mGripFract", ctypes.c_double),
        ("mPressure", ctypes.c_double),                   # kPa
        ("mTemperature", ctypes.c_double * 3),            # inner/center/outer K
        ("mWear", ctypes.c_double),                       # 0..1, 1 = unworn
        ("mTerrainName", ctypes.c_char * 16),
        ("mSurfaceType", ctypes.c_ubyte),
        ("mFlat", ctypes.c_ubyte),
        ("mDetached", ctypes.c_ubyte),
        ("mStaticUndeflectedRadius", ctypes.c_ubyte),
        ("mVerticalTireDeflection", ctypes.c_double),
        ("mWheelYLocation", ctypes.c_double),
        ("mToe", ctypes.c_double),
        ("mTireCarcassTemperature", ctypes.c_double),     # Kelvin
        ("mTireInnerLayerTemperature", ctypes.c_double * 3),
        ("mExpansion", ctypes.c_ubyte * 24),
    ]


class rF2VehicleTelemetry(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mID", ctypes.c_int),
        ("mDeltaTime", ctypes.c_double),
        ("mElapsedTime", ctypes.c_double),
        ("mLapNumber", ctypes.c_int),
        ("mLapStartET", ctypes.c_double),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTrackName", ctypes.c_char * 64),
        ("mPos", rF2Vec3),
        ("mLocalVel", rF2Vec3),
        ("mLocalAccel", rF2Vec3),
        ("mOri", rF2Vec3 * 3),
        ("mLocalRot", rF2Vec3),
        ("mLocalRotAccel", rF2Vec3),
        ("mGear", ctypes.c_int),
        ("mEngineRPM", ctypes.c_double),
        ("mEngineWaterTemp", ctypes.c_double),            # Celsius
        ("mEngineOilTemp", ctypes.c_double),              # Celsius
        ("mClutchRPM", ctypes.c_double),
        ("mUnfilteredThrottle", ctypes.c_double),
        ("mUnfilteredBrake", ctypes.c_double),
        ("mUnfilteredSteering", ctypes.c_double),
        ("mUnfilteredClutch", ctypes.c_double),
        ("mFilteredThrottle", ctypes.c_double),
        ("mFilteredBrake", ctypes.c_double),
        ("mFilteredSteering", ctypes.c_double),
        ("mFilteredClutch", ctypes.c_double),
        ("mSteeringShaftTorque", ctypes.c_double),
        ("mFront3rdDeflection", ctypes.c_double),
        ("mRear3rdDeflection", ctypes.c_double),
        ("mFrontWingHeight", ctypes.c_double),
        ("mFrontRideHeight", ctypes.c_double),
        ("mRearRideHeight", ctypes.c_double),
        ("mDrag", ctypes.c_double),
        ("mFrontDownforce", ctypes.c_double),
        ("mRearDownforce", ctypes.c_double),
        ("mFuel", ctypes.c_double),                       # litres
        ("mEngineMaxRPM", ctypes.c_double),
        ("mScheduledStops", ctypes.c_ubyte),
        ("mOverheating", ctypes.c_ubyte),
        ("mDetached", ctypes.c_ubyte),
        ("mHeadlights", ctypes.c_ubyte),
        ("mDentSeverity", ctypes.c_ubyte * 8),
        ("mLastImpactET", ctypes.c_double),
        ("mLastImpactMagnitude", ctypes.c_double),
        ("mLastImpactPos", rF2Vec3),
        ("mEngineTorque", ctypes.c_double),
        ("mCurrentSector", ctypes.c_int),
        ("mSpeedLimiter", ctypes.c_ubyte),
        ("mMaxGears", ctypes.c_ubyte),
        ("mFrontTireCompoundIndex", ctypes.c_ubyte),
        ("mRearTireCompoundIndex", ctypes.c_ubyte),
        ("mFuelCapacity", ctypes.c_double),
        ("mFrontFlapActivated", ctypes.c_ubyte),
        ("mRearFlapActivated", ctypes.c_ubyte),
        ("mRearFlapLegalStatus", ctypes.c_ubyte),
        ("mIgnitionStarter", ctypes.c_ubyte),
        ("mFrontTireCompoundName", ctypes.c_char * 18),
        ("mRearTireCompoundName", ctypes.c_char * 18),
        ("mSpeedLimiterAvailable", ctypes.c_ubyte),
        ("mAntiStallActivated", ctypes.c_ubyte),
        ("mUnused", ctypes.c_ubyte * 2),
        ("mVisualSteeringWheelRange", ctypes.c_float),
        ("mRearBrakeBias", ctypes.c_double),
        ("mTurboBoostPressure", ctypes.c_double),
        ("mPhysicsToGraphicsOffset", ctypes.c_float * 3),
        ("mPhysicalSteeringWheelRange", ctypes.c_float),
        ("mExpansion", ctypes.c_ubyte * 152),
        ("mWheels", rF2Wheel * 4),                        # FL, FR, RL, RR
    ]


class rF2Telemetry(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_uint),
        ("mVersionUpdateEnd", ctypes.c_uint),
        ("mBytesUpdatedHint", ctypes.c_int),
        ("mNumVehicles", ctypes.c_int),
        ("mVehicles", rF2VehicleTelemetry * MAX_MAPPED_VEHICLES),
    ]


class rF2VehicleScoring(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mID", ctypes.c_int),
        ("mDriverName", ctypes.c_char * 32),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTotalLaps", ctypes.c_short),
        ("mSector", ctypes.c_byte),
        ("mFinishStatus", ctypes.c_byte),
        ("mLapDist", ctypes.c_double),
        ("mPathLateral", ctypes.c_double),
        ("mTrackEdge", ctypes.c_double),
        ("mBestSector1", ctypes.c_double),
        ("mBestSector2", ctypes.c_double),
        ("mBestLapTime", ctypes.c_double),
        ("mLastSector1", ctypes.c_double),
        ("mLastSector2", ctypes.c_double),
        ("mLastLapTime", ctypes.c_double),
        ("mCurSector1", ctypes.c_double),
        ("mCurSector2", ctypes.c_double),
        ("mNumPitstops", ctypes.c_short),
        ("mNumPenalties", ctypes.c_short),
        ("mIsPlayer", ctypes.c_ubyte),
        ("mControl", ctypes.c_byte),
        ("mInPits", ctypes.c_ubyte),
        ("mPlace", ctypes.c_ubyte),
        ("mVehicleClass", ctypes.c_char * 32),
        ("mTimeBehindNext", ctypes.c_double),
        ("mLapsBehindNext", ctypes.c_int),
        ("mTimeBehindLeader", ctypes.c_double),
        ("mLapsBehindLeader", ctypes.c_int),
        ("mLapStartET", ctypes.c_double),
        ("mPos", rF2Vec3),
        ("mLocalVel", rF2Vec3),
        ("mLocalAccel", rF2Vec3),
        ("mOri", rF2Vec3 * 3),
        ("mLocalRot", rF2Vec3),
        ("mLocalRotAccel", rF2Vec3),
        ("mHeadlights", ctypes.c_ubyte),
        ("mPitState", ctypes.c_ubyte),
        ("mServerScored", ctypes.c_ubyte),
        ("mIndividualPhase", ctypes.c_ubyte),
        ("mQualification", ctypes.c_int),
        ("mTimeIntoLap", ctypes.c_double),
        ("mEstimatedLapTime", ctypes.c_double),
        ("mPitGroup", ctypes.c_char * 24),
        ("mFlag", ctypes.c_ubyte),
        ("mUnderYellow", ctypes.c_ubyte),
        ("mCountLapFlag", ctypes.c_ubyte),
        ("mInGarageStall", ctypes.c_ubyte),
        ("mUpgradePack", ctypes.c_ubyte * 16),
        ("mPitLapDist", ctypes.c_float),
        ("mBestLapSector1", ctypes.c_float),
        ("mBestLapSector2", ctypes.c_float),
        ("mExpansion", ctypes.c_ubyte * 48),
    ]


class rF2ScoringInfo(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mTrackName", ctypes.c_char * 64),
        ("mSession", ctypes.c_int),
        ("mCurrentET", ctypes.c_double),
        ("mEndET", ctypes.c_double),
        ("mMaxLaps", ctypes.c_int),
        ("mLapDist", ctypes.c_double),
        ("mResultsStreamPtr", ctypes.c_ubyte * 8),
        ("mNumVehicles", ctypes.c_int),
        ("mGamePhase", ctypes.c_ubyte),
        ("mYellowFlagState", ctypes.c_byte),
        ("mSectorFlag", ctypes.c_byte * 3),
        ("mStartLight", ctypes.c_ubyte),
        ("mNumRedLights", ctypes.c_ubyte),
        ("mInRealtime", ctypes.c_ubyte),
        ("mPlayerName", ctypes.c_char * 32),
        ("mPlrFileName", ctypes.c_char * 64),
        ("mDarkCloud", ctypes.c_double),
        ("mRaining", ctypes.c_double),
        ("mAmbientTemp", ctypes.c_double),
        ("mTrackTemp", ctypes.c_double),
        ("mWind", rF2Vec3),
        ("mMinPathWetness", ctypes.c_double),
        ("mMaxPathWetness", ctypes.c_double),
        ("mGameMode", ctypes.c_ubyte),
        ("mIsPasswordProtected", ctypes.c_ubyte),
        ("mServerPort", ctypes.c_ushort),
        ("mServerPublicIP", ctypes.c_uint),
        ("mMaxPlayers", ctypes.c_int),
        ("mServerName", ctypes.c_char * 32),
        ("mStartET", ctypes.c_float),
        ("mAvgPathWetness", ctypes.c_double),
        ("mExpansion", ctypes.c_ubyte * 200),
        ("mPointer2", ctypes.c_ubyte * 8),
    ]


class rF2Scoring(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", ctypes.c_uint),
        ("mVersionUpdateEnd", ctypes.c_uint),
        ("mBytesUpdatedHint", ctypes.c_int),
        ("mScoringInfo", rF2ScoringInfo),
        ("mVehicles", rF2VehicleScoring * MAX_MAPPED_VEHICLES),
    ]


SESSION_NAMES = {
    0: "Test", 1: "Practice", 2: "Practice", 3: "Practice", 4: "Practice",
    5: "Qualify", 6: "Qualify", 7: "Qualify", 8: "Qualify",
    9: "Warmup", 10: "Race", 11: "Race", 12: "Race", 13: "Race", 14: "Race",
}


def _section_exists(name: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        k.OpenFileMappingW.restype = wintypes.HANDLE
        k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        h = k.OpenFileMappingW(0x0004, False, name)  # FILE_MAP_READ
        if h:
            k.CloseHandle(h)
            return True
        return False
    except Exception:
        return False


class _Reader:
    """Attaches to one shared-memory section and reads it with a torn-read
    guard (version-begin == version-end)."""

    def __init__(self, name: str, struct_type):
        self.name = name
        self.struct_type = struct_type
        self.size = ctypes.sizeof(struct_type)
        self.mm: Optional[mmap.mmap] = None

    def _open(self) -> bool:
        if not _section_exists(self.name):
            self.mm = None
            return False
        try:
            self.mm = mmap.mmap(-1, self.size, tagname=self.name, access=mmap.ACCESS_READ)
            return True
        except Exception:
            self.mm = None
            return False

    def read(self):
        if self.mm is None and not self._open():
            return None
        try:
            for _ in range(4):
                self.mm.seek(0)
                buf = self.mm.read(self.size)
                obj = self.struct_type.from_buffer_copy(buf)
                if obj.mVersionUpdateBegin == obj.mVersionUpdateEnd:
                    return obj
            return obj
        except Exception:
            try:
                self.mm.close()
            except Exception:
                pass
            self.mm = None
            return None

    def close(self):
        if self.mm:
            try:
                self.mm.close()
            except Exception:
                pass
        self.mm = None


class LMUSource(SourceBase):
    name = "LMU"

    def __init__(self):
        self._tele = _Reader(TELEMETRY_SHM, rF2Telemetry)
        self._scor = _Reader(SCORING_SHM, rF2Scoring)
        self._last_et = -1.0
        self._last_change = 0.0

    @staticmethod
    def available() -> bool:
        return _section_exists(TELEMETRY_SHM) or _section_exists(SCORING_SHM)

    def start(self):
        pass

    def stop(self):
        self._tele.close()
        self._scor.close()

    def is_live(self) -> bool:
        return (time.monotonic() - self._last_change) < 1.5

    def poll(self) -> Frame:
        now = time.monotonic()
        f = Frame(t=now, game="LMU")
        tele = self._tele.read()
        scor = self._scor.read()
        if tele is None or scor is None or tele.mNumVehicles <= 0:
            return f

        si = scor.mScoringInfo
        f.track = _s(si.mTrackName) or _s(tele.mVehicles[0].mTrackName)
        f.session = SESSION_NAMES.get(si.mSession, "Session")
        f.num_cars = max(0, int(si.mNumVehicles))
        f.track_len = si.mLapDist if si.mLapDist > 0 else 0.0
        f.total_laps = max(0, int(si.mMaxLaps)) if si.mMaxLaps < 9999 else 0

        # --- find the player in scoring ---
        ps = None
        for i in range(min(scor.mNumVehicles, MAX_MAPPED_VEHICLES)):
            v = scor.mVehicles[i]
            if v.mIsPlayer:
                ps = v
                break
        if ps is None and scor.mNumVehicles > 0:
            ps = scor.mVehicles[0]

        # --- matching telemetry vehicle (by mID) ---
        vt = None
        if ps is not None:
            for i in range(min(tele.mNumVehicles, MAX_MAPPED_VEHICLES)):
                if tele.mVehicles[i].mID == ps.mID:
                    vt = tele.mVehicles[i]
                    break
        if vt is None and tele.mNumVehicles > 0:
            vt = tele.mVehicles[0]

        if vt is not None:
            v = vt.mLocalVel
            f.speed = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) * 3.6
            f.rpm = vt.mEngineRPM
            f.max_rpm = vt.mEngineMaxRPM
            f.gear = int(vt.mGear)
            f.throttle = _clamp01(vt.mFilteredThrottle)
            f.brake = _clamp01(vt.mFilteredBrake)
            f.clutch = _clamp01(vt.mFilteredClutch)
            f.steer = max(-1.0, min(1.0, vt.mFilteredSteering))
            f.fuel = vt.mFuel
            f.fuel_capacity = vt.mFuelCapacity
            f.water_temp = vt.mEngineWaterTemp
            f.oil_temp = vt.mEngineOilTemp
            f.drs = int(vt.mRearFlapActivated)
            f.turbo = vt.mTurboBoostPressure / 100000.0  # Pa -> bar
            f.lap = int(vt.mLapNumber)
            for i in range(4):
                w = vt.mWheels[i]
                f.tyre_temp[i] = w.mTemperature[1] - KELVIN      # centre
                f.tyre_press[i] = w.mPressure * 0.1450377        # kPa -> psi
                f.tyre_life[i] = _clamp01(w.mWear) * 100.0       # 1 = fresh
                f.brake_temp[i] = w.mBrakeTemp - KELVIN
            # detect live data by elapsed-time advancing
            et = vt.mElapsedTime
            if et != self._last_et:
                self._last_et = et
                self._last_change = now

        if ps is not None:
            f.position = int(ps.mPlace)
            f.lap_dist = ps.mLapDist
            f.sector = int(ps.mSector)
            f.last_lap = ps.mLastLapTime if ps.mLastLapTime > 0 else 0.0
            f.best_lap = ps.mBestLapTime if ps.mBestLapTime > 0 else 0.0
            f.cur_lap_time = ps.mTimeIntoLap if ps.mTimeIntoLap > 0 else 0.0
            f.pos_x = ps.mPos.x
            f.pos_y = ps.mPos.z

        f.connected = self.is_live()
        return f


def _s(b: bytes) -> str:
    try:
        return b.decode("utf-8", "ignore").strip("\x00").strip()
    except Exception:
        return ""


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)
