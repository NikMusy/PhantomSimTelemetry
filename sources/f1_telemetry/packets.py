"""ctypes definitions for F1 25 / 2026 Season Pack UDP packets.

All packets are little-endian, no padding (pack=1). Field layouts match the
official "Data Output from F1 25" specification (packetFormat 2025).
"""
import ctypes
import struct

from . import spec

u8 = ctypes.c_uint8
i8 = ctypes.c_int8
u16 = ctypes.c_uint16
i16 = ctypes.c_int16
u32 = ctypes.c_uint32
i32 = ctypes.c_int32
u64 = ctypes.c_uint64
f32 = ctypes.c_float


class _Base(ctypes.LittleEndianStructure):
    _pack_ = 1

    def to_dict(self):
        out = {}
        for name, _ in self._fields_:
            val = getattr(self, name)
            if isinstance(val, ctypes.Array):
                val = list(val)
            out[name] = val
        return out


class PacketHeader(_Base):
    _fields_ = [
        ("packetFormat", u16),
        ("gameYear", u8),
        ("gameMajorVersion", u8),
        ("gameMinorVersion", u8),
        ("packetVersion", u8),
        ("packetId", u8),
        ("sessionUID", u64),
        ("sessionTime", f32),
        ("frameIdentifier", u32),
        ("overallFrameIdentifier", u32),
        ("playerCarIndex", u8),
        ("secondaryPlayerCarIndex", u8),
    ]


HEADER_SIZE = ctypes.sizeof(PacketHeader)  # 29


# --- Motion (id 0) --------------------------------------------------------
class CarMotionData(_Base):
    _fields_ = [
        ("worldPositionX", f32),
        ("worldPositionY", f32),
        ("worldPositionZ", f32),
        ("worldVelocityX", f32),
        ("worldVelocityY", f32),
        ("worldVelocityZ", f32),
        ("worldForwardDirX", i16),
        ("worldForwardDirY", i16),
        ("worldForwardDirZ", i16),
        ("worldRightDirX", i16),
        ("worldRightDirY", i16),
        ("worldRightDirZ", i16),
        ("gForceLateral", f32),
        ("gForceLongitudinal", f32),
        ("gForceVertical", f32),
        ("yaw", f32),
        ("pitch", f32),
        ("roll", f32),
    ]


class PacketMotionData(_Base):
    _fields_ = [
        ("header", PacketHeader),
        ("carMotionData", CarMotionData * 22),
    ]


# --- Car Telemetry (id 6) -------------------------------------------------
class CarTelemetryData(_Base):
    _fields_ = [
        ("speed", u16),
        ("throttle", f32),
        ("steer", f32),
        ("brake", f32),
        ("clutch", u8),
        ("gear", i8),
        ("engineRPM", u16),
        ("drs", u8),
        ("revLightsPercent", u8),
        ("revLightsBitValue", u16),
        ("brakesTemperature", u16 * 4),
        ("tyresSurfaceTemperature", u8 * 4),
        ("tyresInnerTemperature", u8 * 4),
        ("engineTemperature", u16),
        ("tyresPressure", f32 * 4),
        ("surfaceType", u8 * 4),
    ]


class PacketCarTelemetryData(_Base):
    _fields_ = [
        ("header", PacketHeader),
        ("carTelemetryData", CarTelemetryData * 22),
        ("mfdPanelIndex", u8),
        ("mfdPanelIndexSecondaryPlayer", u8),
        ("suggestedGear", i8),
    ]


# --- Lap Data (id 2) ------------------------------------------------------
class LapData(_Base):
    _fields_ = [
        ("lastLapTimeInMS", u32),
        ("currentLapTimeInMS", u32),
        ("sector1TimeMSPart", u16),
        ("sector1TimeMinutesPart", u8),
        ("sector2TimeMSPart", u16),
        ("sector2TimeMinutesPart", u8),
        ("deltaToCarInFrontMSPart", u16),
        ("deltaToCarInFrontMinutesPart", u8),
        ("deltaToRaceLeaderMSPart", u16),
        ("deltaToRaceLeaderMinutesPart", u8),
        ("lapDistance", f32),
        ("totalDistance", f32),
        ("safetyCarDelta", f32),
        ("carPosition", u8),
        ("currentLapNum", u8),
        ("pitStatus", u8),
        ("numPitStops", u8),
        ("sector", u8),
        ("currentLapInvalid", u8),
        ("penalties", u8),
        ("totalWarnings", u8),
        ("cornerCuttingWarnings", u8),
        ("numUnservedDriveThroughPens", u8),
        ("numUnservedStopGoPens", u8),
        ("gridPosition", u8),
        ("driverStatus", u8),
        ("resultStatus", u8),
        ("pitLaneTimerActive", u8),
        ("pitLaneTimeInLaneInMS", u16),
        ("pitStopTimerInMS", u16),
        ("pitStopShouldServePen", u8),
        ("speedTrapFastestSpeed", f32),
        ("speedTrapFastestLap", u8),
    ]

    @property
    def deltaToLeaderMS(self):
        return self.deltaToRaceLeaderMinutesPart * 60000 + self.deltaToRaceLeaderMSPart

    @property
    def deltaToFrontMS(self):
        return self.deltaToCarInFrontMinutesPart * 60000 + self.deltaToCarInFrontMSPart

    @property
    def sector1MS(self):
        return self.sector1TimeMinutesPart * 60000 + self.sector1TimeMSPart

    @property
    def sector2MS(self):
        return self.sector2TimeMinutesPart * 60000 + self.sector2TimeMSPart


class PacketLapData(_Base):
    _fields_ = [
        ("header", PacketHeader),
        ("lapData", LapData * 22),
        ("timeTrialPBCarIdx", u8),
        ("timeTrialRivalCarIdx", u8),
    ]


# --- Car Status (id 7) ----------------------------------------------------
class CarStatusData(_Base):
    _fields_ = [
        ("tractionControl", u8),
        ("antiLockBrakes", u8),
        ("fuelMix", u8),
        ("frontBrakeBias", u8),
        ("pitLimiterStatus", u8),
        ("fuelInTank", f32),
        ("fuelCapacity", f32),
        ("fuelRemainingLaps", f32),
        ("maxRPM", u16),
        ("idleRPM", u16),
        ("maxGears", u8),
        ("drsAllowed", u8),
        ("drsActivationDistance", u16),
        ("actualTyreCompound", u8),
        ("visualTyreCompound", u8),
        ("tyresAgeLaps", u8),
        ("vehicleFiaFlags", i8),
        ("enginePowerICE", f32),
        ("enginePowerMGUK", f32),
        ("ersStoreEnergy", f32),
        ("ersDeployMode", u8),
        ("ersHarvestedThisLapMGUK", f32),
        ("ersHarvestedThisLapMGUH", f32),
        ("ersDeployedThisLap", f32),
        ("networkPaused", u8),
    ]


class PacketCarStatusData(_Base):
    _fields_ = [
        ("header", PacketHeader),
        ("carStatusData", CarStatusData * 22),
    ]


# --- Car Damage (id 10) ---------------------------------------------------
class CarDamageData(_Base):
    _fields_ = [
        ("tyresWear", f32 * 4),
        ("tyresDamage", u8 * 4),
        ("brakesDamage", u8 * 4),
        ("tyreBlisters", u8 * 4),
        ("frontLeftWingDamage", u8),
        ("frontRightWingDamage", u8),
        ("rearWingDamage", u8),
        ("floorDamage", u8),
        ("diffuserDamage", u8),
        ("sidepodDamage", u8),
        ("drsFault", u8),
        ("ersFault", u8),
        ("gearBoxDamage", u8),
        ("engineDamage", u8),
        ("engineMGUHWear", u8),
        ("engineESWear", u8),
        ("engineCEWear", u8),
        ("engineICEWear", u8),
        ("engineMGUKWear", u8),
        ("engineTCWear", u8),
        ("engineBlown", u8),
        ("engineSeized", u8),
    ]


class PacketCarDamageData(_Base):
    _fields_ = [
        ("header", PacketHeader),
        ("carDamageData", CarDamageData * 22),
    ]


# --- Participants (id 4) --------------------------------------------------
class LiveryColour(_Base):
    _fields_ = [("red", u8), ("green", u8), ("blue", u8)]


class ParticipantData(_Base):
    _fields_ = [
        ("aiControlled", u8),
        ("driverId", u8),
        ("networkId", u8),
        ("teamId", u8),
        ("myTeam", u8),
        ("raceNumber", u8),
        ("nationality", u8),
        ("name", ctypes.c_char * 32),
        ("yourTelemetry", u8),
        ("showOnlineNames", u8),
        ("techLevel", u16),
        ("platform", u8),
        ("numColours", u8),
        ("liveryColours", LiveryColour * 4),
    ]

    @property
    def name_str(self):
        try:
            return self.name.decode("utf-8", "replace").rstrip("\x00").strip()
        except Exception:
            return ""


class PacketParticipantsData(_Base):
    _fields_ = [
        ("header", PacketHeader),
        ("numActiveCars", u8),
        ("participants", ParticipantData * 22),
    ]


# --- Manual parsers for variable / large packets --------------------------

class SessionInfo:
    """Lightweight container parsed from the stable prefix of the Session packet."""
    __slots__ = (
        "weather", "trackTemperature", "airTemperature", "totalLaps",
        "trackLength", "sessionType", "trackId", "formula", "sessionTimeLeft",
        "sessionDuration", "pitSpeedLimit", "gamePaused", "safetyCarStatus",
        "networkGame", "forecast", "header",
    )

    def __init__(self):
        for s in self.__slots__:
            setattr(self, s, None)
        self.forecast = []


# Session prefix: from byte 29 onward, 19 bytes up to numMarshalZones.
_SESSION_PREFIX = struct.Struct("<BbbBHBbBHHBBBBBB")
# safetyCarStatus, networkGame, numWeatherForecastSamples
_SESSION_MID = struct.Struct("<BBB")
# One weather forecast sample = 8 bytes.
_FORECAST = struct.Struct("<BBBbbbbB")
_MARSHAL_ZONES_BYTES = 21 * 5  # MarshalZone[21], each float+int8


def parse_session(data, header):
    """Parse the parts of PacketSessionData we care about (robust to trailing
    layout changes — only the stable leading fields are read)."""
    try:
        s = SessionInfo()
        s.header = header
        (s.weather, s.trackTemperature, s.airTemperature, s.totalLaps,
         s.trackLength, s.sessionType, s.trackId, s.formula, s.sessionTimeLeft,
         s.sessionDuration, s.pitSpeedLimit, s.gamePaused, _isSpectating,
         _spectatorIdx, _sliPro, _numMarshalZones) = _SESSION_PREFIX.unpack_from(
            data, HEADER_SIZE)

        mid_off = HEADER_SIZE + _SESSION_PREFIX.size + _MARSHAL_ZONES_BYTES
        s.safetyCarStatus, s.networkGame, num_forecast = _SESSION_MID.unpack_from(
            data, mid_off)

        fc_off = mid_off + _SESSION_MID.size
        num_forecast = max(0, min(num_forecast, 64))
        for i in range(num_forecast):
            off = fc_off + i * _FORECAST.size
            if off + _FORECAST.size > len(data):
                break
            (stype, toff, weather, ttemp, ttc, atemp, atc, rain) = \
                _FORECAST.unpack_from(data, off)
            s.forecast.append({
                "sessionType": stype, "timeOffset": toff, "weather": weather,
                "trackTemp": ttemp, "trackTempChange": ttc, "airTemp": atemp,
                "airTempChange": atc, "rain": rain,
            })
        return s
    except Exception:
        return None


# Event packet: header + 4-char string code + union of details.
def parse_event(data, header):
    try:
        code = bytes(data[HEADER_SIZE:HEADER_SIZE + 4]).decode("ascii", "ignore")
        detail_off = HEADER_SIZE + 4
        out = {"code": code, "header": header}
        if code == "FTLP":  # fastest lap: vehicleIdx (u8), lapTime (f32)
            vidx, ltime = struct.unpack_from("<Bf", data, detail_off)
            out["vehicleIdx"] = vidx
            out["lapTime"] = ltime
        elif code in ("RTMT", "TMPT", "RCWN", "STLG", "DRSD", "DRSE",
                       "RTRY", "OVTK"):
            try:
                out["vehicleIdx"] = data[detail_off]
            except Exception:
                pass
        elif code == "PENA":  # penalty type, infringement, vehicleIdx, ...
            try:
                ptype, infr, vidx, other, time_, lapn, places = \
                    struct.unpack_from("<7B", data, detail_off)
                out.update({"penaltyType": ptype, "infringement": infr,
                            "vehicleIdx": vidx, "time": time_, "lapNum": lapn})
            except Exception:
                pass
        elif code == "SPTP":  # speed trap
            try:
                vidx, speed = struct.unpack_from("<Bf", data, detail_off)
                out["vehicleIdx"] = vidx
                out["speed"] = speed
            except Exception:
                pass
        return out
    except Exception:
        return None


# Map packetId -> (kind, parser). kind 'struct' uses from_buffer_copy.
STRUCT_PACKETS = {
    spec.PACKET_MOTION: PacketMotionData,
    spec.PACKET_CAR_TELEMETRY: PacketCarTelemetryData,
    spec.PACKET_LAP_DATA: PacketLapData,
    spec.PACKET_CAR_STATUS: PacketCarStatusData,
    spec.PACKET_CAR_DAMAGE: PacketCarDamageData,
    spec.PACKET_PARTICIPANTS: PacketParticipantsData,
}


def parse_packet(data):
    """Parse a raw datagram into (packetId, object) or None.

    object is a ctypes packet for struct packets, a SessionInfo for session,
    a dict for event, else None for ignored packet types (still returns id).
    """
    if len(data) < HEADER_SIZE:
        return None
    header = PacketHeader.from_buffer_copy(data[:HEADER_SIZE])
    pid = header.packetId

    cls = STRUCT_PACKETS.get(pid)
    if cls is not None:
        size = ctypes.sizeof(cls)
        if len(data) >= size:
            try:
                return pid, cls.from_buffer_copy(data[:size]), header
            except Exception:
                return pid, None, header
        return pid, None, header
    if pid == spec.PACKET_SESSION:
        return pid, parse_session(data, header), header
    if pid == spec.PACKET_EVENT:
        return pid, parse_event(data, header), header
    return pid, None, header
