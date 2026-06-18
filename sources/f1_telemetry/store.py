"""Central telemetry state + derived strategy maths.

Lives on the GUI thread (mutated only from the packet slot), so no locking is
needed. The UI reads attributes directly and a render timer paints at ~30fps.
"""
import time
from collections import deque

from . import spec


class CarState:
    """Per-car rolling state used by the timing tower."""
    __slots__ = (
        "active", "name", "team_id", "position", "grid_position",
        "last_lap_ms", "best_lap_ms", "current_lap", "num_pit_stops",
        "visual_compound", "actual_compound", "tyre_age", "pit_status",
        "penalties", "delta_leader_ms", "delta_front_ms", "result_status",
        "driver_status", "sector", "current_lap_ms", "lap_distance",
        "tyre_wear_avg", "speed_trap", "best_s1", "best_s2", "cur_s1", "cur_s2",
        "race_number",
    )

    def __init__(self):
        self.active = False
        self.name = ""
        self.team_id = 255
        self.position = 0
        self.grid_position = 0
        self.last_lap_ms = 0
        self.best_lap_ms = 0
        self.current_lap = 0
        self.num_pit_stops = 0
        self.visual_compound = 0
        self.actual_compound = 0
        self.tyre_age = 0
        self.pit_status = 0
        self.penalties = 0
        self.delta_leader_ms = 0
        self.delta_front_ms = 0
        self.result_status = 0
        self.driver_status = 0
        self.sector = 0
        self.current_lap_ms = 0
        self.lap_distance = 0.0
        self.tyre_wear_avg = 0.0
        self.speed_trap = 0.0
        self.best_s1 = 0
        self.best_s2 = 0
        self.cur_s1 = 0
        self.cur_s2 = 0
        self.race_number = 0


class TelemetryStore:
    def __init__(self):
        self.connected = False
        self.player_idx = 0
        self.game_year = 0
        self.packet_format = 0

        # packet stats
        self.total_packets = 0
        self._pkt_window = deque(maxlen=240)  # timestamps for rate calc
        self.last_packet_time = 0.0

        # session
        self.session = None       # packets.SessionInfo
        self.track_id = -1
        self.session_type = 0
        self.total_laps = 0
        self.session_time_left = 0
        self.weather = 0
        self.air_temp = 0
        self.track_temp = 0
        self.pit_speed_limit = 0
        self.safety_car = 0
        self.forecast = []

        # cars
        self.cars = [CarState() for _ in range(22)]
        self.num_active = 0

        # player telemetry (id 6)
        self.speed = 0
        self.gear = 0
        self.rpm = 0
        self.max_rpm = 13000
        self.throttle = 0.0
        self.brake = 0.0
        self.clutch = 0
        self.steer = 0.0
        self.drs = 0
        self.rev_lights = 0
        self.engine_temp = 0
        self.brake_temps = [0, 0, 0, 0]
        self.tyre_surface_temp = [0, 0, 0, 0]
        self.tyre_inner_temp = [0, 0, 0, 0]
        self.tyre_pressure = [0.0, 0.0, 0.0, 0.0]
        self.surface_type = [0, 0, 0, 0]

        # player status (id 7)
        self.fuel_mix = 1
        self.front_brake_bias = 50
        self.fuel_in_tank = 0.0
        self.fuel_capacity = 110.0
        self.fuel_remaining_laps = 0.0
        self.drs_allowed = 0
        self.visual_compound = 0
        self.actual_compound = 0
        self.tyre_age = 0
        self.fia_flag = 0
        self.ers_store = 0.0
        self.ers_mode = 0
        self.ers_harvested_mguk = 0.0
        self.ers_harvested_mguh = 0.0
        self.ers_deployed = 0.0
        self.pit_limiter = 0

        # player damage (id 10)
        self.tyre_wear = [0.0, 0.0, 0.0, 0.0]
        self.tyre_damage = [0, 0, 0, 0]
        self.brake_damage = [0, 0, 0, 0]
        self.tyre_blisters = [0, 0, 0, 0]
        self.wing_damage = [0, 0]   # FL, FR
        self.rear_wing_damage = 0
        self.floor_damage = 0
        self.diffuser_damage = 0
        self.engine_wear = 0
        self.gearbox_wear = 0

        # player lap (id 2)
        self.position = 0
        self.current_lap = 0
        self.last_lap_ms = 0
        self.best_lap_ms = 0
        self.current_lap_ms = 0
        self.sector = 0
        self.sector1_ms = 0
        self.sector2_ms = 0
        self.delta_leader_ms = 0
        self.delta_front_ms = 0
        self.lap_distance = 0.0
        self.pit_status = 0
        self.num_pit_stops = 0
        self.lap_invalid = 0
        self.penalties = 0
        self.warnings = 0
        self.safety_car_delta = 0.0
        self.pit_lane_time_ms = 0
        self.pit_stop_timer_ms = 0

        # derived / history
        self.lap_history = []     # list of dicts: lap, time_ms, fuel, wear, compound
        self._last_seen_lap = -1
        self._fuel_at_lap_start = None
        self._wear_at_lap_start = None
        self.fuel_per_lap = 0.0
        self.wear_per_lap = 0.0
        self._fuel_deltas = deque(maxlen=5)
        self._wear_deltas = deque(maxlen=5)

        # events / engineer radio
        self.events = deque(maxlen=60)

        # nearby-car gap history (for the Circle of Doom + trend graphs)
        self.gap_ahead_hist = deque(maxlen=400)    # (t, gap_seconds)
        self.gap_behind_hist = deque(maxlen=400)
        self._last_gap_track = 0.0

        # motion / track map
        self.car_xy = [(0.0, 0.0) for _ in range(22)]
        self.track_pts = []          # recorded outline (player path) [(x, z)]
        self._last_track_pt = None
        # session-best sector / lap colouring
        self.fastest_lap_ms = 0
        self.fastest_lap_idx = -1
        self.best_s1_overall = 0
        self.best_s2_overall = 0

    # -- packet stats ------------------------------------------------------
    def mark_packet(self):
        now = time.monotonic()
        self.total_packets += 1
        self.last_packet_time = now
        self._pkt_window.append(now)
        self.connected = True

    def packet_rate(self):
        if len(self._pkt_window) < 2:
            return 0.0
        span = self._pkt_window[-1] - self._pkt_window[0]
        if span <= 0:
            return 0.0
        return (len(self._pkt_window) - 1) / span

    def is_live(self):
        return self.connected and (time.monotonic() - self.last_packet_time) < 2.0

    # -- main dispatch -----------------------------------------------------
    def update(self, pid, obj, header):
        self.mark_packet()
        if header is not None:
            self.player_idx = header.playerCarIndex
            self.game_year = header.gameYear
            self.packet_format = header.packetFormat
        if obj is None:
            return
        if pid == spec.PACKET_MOTION:
            self._on_motion(obj)
        elif pid == spec.PACKET_CAR_TELEMETRY:
            self._on_telemetry(obj)
        elif pid == spec.PACKET_LAP_DATA:
            self._on_lap(obj)
        elif pid == spec.PACKET_CAR_STATUS:
            self._on_status(obj)
        elif pid == spec.PACKET_CAR_DAMAGE:
            self._on_damage(obj)
        elif pid == spec.PACKET_PARTICIPANTS:
            self._on_participants(obj)
        elif pid == spec.PACKET_SESSION:
            self._on_session(obj)
        elif pid == spec.PACKET_EVENT:
            self._on_event(obj)

    # -- handlers ----------------------------------------------------------
    def _on_motion(self, pkt):
        for i in range(22):
            m = pkt.carMotionData[i]
            self.car_xy[i] = (m.worldPositionX, m.worldPositionZ)
        px, pz = self.car_xy[self.player_idx] if self.player_idx < 22 else (0, 0)
        if px or pz:
            lp = self._last_track_pt
            if lp is None or (px - lp[0]) ** 2 + (pz - lp[1]) ** 2 > 64:
                self.track_pts.append((px, pz))
                self._last_track_pt = (px, pz)
                if len(self.track_pts) > 800:
                    self.track_pts.pop(0)

    def _on_telemetry(self, pkt):
        i = self.player_idx
        if i >= 22:
            return
        t = pkt.carTelemetryData[i]
        self.speed = t.speed
        self.gear = t.gear
        self.rpm = t.engineRPM
        self.throttle = t.throttle
        self.brake = t.brake
        self.clutch = t.clutch
        self.steer = t.steer
        self.drs = t.drs
        self.rev_lights = t.revLightsPercent
        self.engine_temp = t.engineTemperature
        self.brake_temps = list(t.brakesTemperature)
        self.tyre_surface_temp = list(t.tyresSurfaceTemperature)
        self.tyre_inner_temp = list(t.tyresInnerTemperature)
        self.tyre_pressure = list(t.tyresPressure)
        self.surface_type = list(t.surfaceType)

    def _on_lap(self, pkt):
        for idx in range(22):
            ld = pkt.lapData[idx]
            car = self.cars[idx]
            car.position = ld.carPosition
            car.grid_position = ld.gridPosition
            car.current_lap = ld.currentLapNum
            car.last_lap_ms = ld.lastLapTimeInMS
            car.num_pit_stops = ld.numPitStops
            car.pit_status = ld.pitStatus
            car.penalties = ld.penalties
            car.delta_leader_ms = ld.deltaToLeaderMS
            car.delta_front_ms = ld.deltaToFrontMS
            car.result_status = ld.resultStatus
            car.driver_status = ld.driverStatus
            car.sector = ld.sector
            car.current_lap_ms = ld.currentLapTimeInMS
            car.lap_distance = ld.lapDistance
            car.speed_trap = ld.speedTrapFastestSpeed
            if ld.lastLapTimeInMS > 0 and (
                    car.best_lap_ms == 0 or ld.lastLapTimeInMS < car.best_lap_ms):
                car.best_lap_ms = ld.lastLapTimeInMS
            if ld.lastLapTimeInMS > 0 and (
                    self.fastest_lap_ms == 0 or ld.lastLapTimeInMS < self.fastest_lap_ms):
                self.fastest_lap_ms = ld.lastLapTimeInMS
                self.fastest_lap_idx = idx
            # sector bests (use completed sectors of the current lap)
            car.cur_s1 = ld.sector1MS
            car.cur_s2 = ld.sector2MS
            if ld.sector >= 1 and ld.sector1MS > 0:
                if car.best_s1 == 0 or ld.sector1MS < car.best_s1:
                    car.best_s1 = ld.sector1MS
                if self.best_s1_overall == 0 or ld.sector1MS < self.best_s1_overall:
                    self.best_s1_overall = ld.sector1MS
            if ld.sector >= 2 and ld.sector2MS > 0:
                if car.best_s2 == 0 or ld.sector2MS < car.best_s2:
                    car.best_s2 = ld.sector2MS
                if self.best_s2_overall == 0 or ld.sector2MS < self.best_s2_overall:
                    self.best_s2_overall = ld.sector2MS
            if ld.resultStatus in (2, 3):
                car.active = True

        i = self.player_idx
        if i < 22:
            ld = pkt.lapData[i]
            self.position = ld.carPosition
            self.current_lap = ld.currentLapNum
            self.last_lap_ms = ld.lastLapTimeInMS
            self.best_lap_ms = self.cars[i].best_lap_ms
            self.current_lap_ms = ld.currentLapTimeInMS
            self.sector = ld.sector
            self.sector1_ms = ld.sector1MS
            self.sector2_ms = ld.sector2MS
            self.delta_leader_ms = ld.deltaToLeaderMS
            self.delta_front_ms = ld.deltaToFrontMS
            self.lap_distance = ld.lapDistance
            self.pit_status = ld.pitStatus
            self.num_pit_stops = ld.numPitStops
            self.lap_invalid = ld.currentLapInvalid
            self.penalties = ld.penalties
            self.warnings = ld.totalWarnings
            self.safety_car_delta = ld.safetyCarDelta
            self.pit_lane_time_ms = ld.pitLaneTimeInLaneInMS
            self.pit_stop_timer_ms = ld.pitStopTimerInMS
            self._track_player_lap(ld.currentLapNum, ld.lastLapTimeInMS)
            self._track_nearby_gaps()

    def _track_player_lap(self, lap_num, last_lap_ms):
        if lap_num != self._last_seen_lap:
            # a new lap just started -> finalise the previous lap's metrics
            if self._last_seen_lap >= 0 and last_lap_ms > 0:
                rec = {
                    "lap": self._last_seen_lap,
                    "time_ms": last_lap_ms,
                    "fuel": self.fuel_in_tank,
                    "wear": sum(self.tyre_wear) / 4.0,
                    "compound": self.visual_compound,
                }
                self.lap_history.append(rec)
                if len(self.lap_history) > 60:
                    self.lap_history.pop(0)
                # fuel/wear per-lap deltas
                if self._fuel_at_lap_start is not None:
                    used = self._fuel_at_lap_start - self.fuel_in_tank
                    if 0 < used < 10:
                        self._fuel_deltas.append(used)
                if self._wear_at_lap_start is not None:
                    dw = (sum(self.tyre_wear) / 4.0) - self._wear_at_lap_start
                    if 0 <= dw < 20:
                        self._wear_deltas.append(dw)
                self._recompute_rates()
            self._last_seen_lap = lap_num
            self._fuel_at_lap_start = self.fuel_in_tank
            self._wear_at_lap_start = sum(self.tyre_wear) / 4.0

    def _recompute_rates(self):
        if self._fuel_deltas:
            self.fuel_per_lap = sorted(self._fuel_deltas)[len(self._fuel_deltas) // 2]
        if self._wear_deltas:
            self.wear_per_lap = sorted(self._wear_deltas)[len(self._wear_deltas) // 2]

    def _on_status(self, pkt):
        for idx in range(22):
            cs = pkt.carStatusData[idx]
            car = self.cars[idx]
            car.visual_compound = cs.visualTyreCompound
            car.actual_compound = cs.actualTyreCompound
            car.tyre_age = cs.tyresAgeLaps
        i = self.player_idx
        if i >= 22:
            return
        cs = pkt.carStatusData[i]
        self.fuel_mix = cs.fuelMix
        self.front_brake_bias = cs.frontBrakeBias
        self.fuel_in_tank = cs.fuelInTank
        self.fuel_capacity = cs.fuelCapacity
        self.fuel_remaining_laps = cs.fuelRemainingLaps
        self.max_rpm = cs.maxRPM or self.max_rpm
        self.drs_allowed = cs.drsAllowed
        self.visual_compound = cs.visualTyreCompound
        self.actual_compound = cs.actualTyreCompound
        self.tyre_age = cs.tyresAgeLaps
        self.fia_flag = cs.vehicleFiaFlags
        self.ers_store = cs.ersStoreEnergy
        self.ers_mode = cs.ersDeployMode
        self.ers_harvested_mguk = cs.ersHarvestedThisLapMGUK
        self.ers_harvested_mguh = cs.ersHarvestedThisLapMGUH
        self.ers_deployed = cs.ersDeployedThisLap
        self.pit_limiter = cs.pitLimiterStatus

    def _on_damage(self, pkt):
        i = self.player_idx
        for idx in range(22):
            cd = pkt.carDamageData[idx]
            self.cars[idx].tyre_wear_avg = sum(cd.tyresWear) / 4.0
        if i >= 22:
            return
        cd = pkt.carDamageData[i]
        self.tyre_wear = list(cd.tyresWear)
        self.tyre_damage = list(cd.tyresDamage)
        self.brake_damage = list(cd.brakesDamage)
        self.tyre_blisters = list(cd.tyreBlisters)
        self.wing_damage = [cd.frontLeftWingDamage, cd.frontRightWingDamage]
        self.rear_wing_damage = cd.rearWingDamage
        self.floor_damage = cd.floorDamage
        self.diffuser_damage = cd.diffuserDamage
        self.engine_wear = cd.engineDamage
        self.gearbox_wear = cd.gearBoxDamage

    def _on_participants(self, pkt):
        self.num_active = pkt.numActiveCars
        for idx in range(22):
            p = pkt.participants[idx]
            car = self.cars[idx]
            car.team_id = p.teamId
            car.race_number = p.raceNumber
            nm = p.name_str
            if nm:
                car.name = nm
            elif not car.name:
                car.name = f"CAR {idx + 1}"
            if idx < pkt.numActiveCars:
                car.active = True

    def _on_session(self, s):
        if s is None:
            return
        self.session = s
        self.track_id = s.trackId if s.trackId is not None else -1
        self.session_type = s.sessionType or 0
        self.total_laps = s.totalLaps or 0
        self.session_time_left = s.sessionTimeLeft or 0
        self.weather = s.weather or 0
        self.air_temp = s.airTemperature or 0
        self.track_temp = s.trackTemperature or 0
        self.pit_speed_limit = s.pitSpeedLimit or 0
        self.safety_car = s.safetyCarStatus or 0
        self.forecast = s.forecast or []

    def _on_event(self, ev):
        if ev is None:
            return
        code = ev.get("code", "")
        msg = self._event_message(ev)
        if msg:
            self.events.appendleft({"t": time.monotonic(), "code": code, "msg": msg})

    def _event_message(self, ev):
        code = ev.get("code", "")
        vidx = ev.get("vehicleIdx")
        who = ""
        if vidx is not None and 0 <= vidx < 22 and self.cars[vidx].name:
            who = self.cars[vidx].name
        table = {
            "SSTA": "Сессия началась",
            "SEND": "Сессия завершена",
            "FTLP": f"Быстрейший круг: {who} {spec.fmt_laptime_ms(int(ev.get('lapTime', 0) * 1000))}",
            "RTMT": f"Сход: {who}",
            "DRSE": "DRS разрешён",
            "DRSD": "DRS запрещён",
            "CHQF": "Клетчатый флаг",
            "RCWN": f"Победитель: {who}",
            "PENA": f"Штраф: {who}",
            "SPTP": f"Speed trap: {who} {ev.get('speed', 0):.1f} км/ч",
            "STLG": "Старт: гаснут огни",
            "LGOT": "Старт! Поехали",
            "RDFL": "Красный флаг",
            "SCAR": "Машина безопасности",
            "OVTK": f"Обгон: {who}",
            "TMPT": f"Командный приказ: {who}",
        }
        return table.get(code, "")

    # -- nearby cars / Circle of Doom -------------------------------------
    def _track_nearby_gaps(self):
        now = time.monotonic()
        if now - self._last_gap_track < 0.1:
            return
        self._last_gap_track = now
        gap_ahead = self.delta_front_ms / 1000.0 if self.position > 1 else 0.0
        behind = None
        for c in self.cars:
            if c.position == self.position + 1:
                behind = c
                break
        gap_behind = behind.delta_front_ms / 1000.0 if behind else 0.0
        self.gap_ahead_hist.append((now, gap_ahead))
        self.gap_behind_hist.append((now, gap_behind))

    def nearby_cars(self, n=3):
        """Cars within +/- n positions of the player, with signed gap in
        seconds (negative = ahead, positive = behind)."""
        me = self.position
        if not me:
            return []
        out = []
        for i, c in enumerate(self.cars):
            if not c.active or not c.position:
                continue
            if abs(c.position - me) <= n:
                gap = (c.delta_leader_ms - self.delta_leader_ms) / 1000.0
                out.append((i, c, gap))
        out.sort(key=lambda x: x[1].position)
        return out

    def gap_to_ahead(self):
        return self.delta_front_ms / 1000.0 if self.position > 1 else 0.0

    def gap_to_behind(self):
        for c in self.cars:
            if c.position == self.position + 1:
                return c.delta_front_ms / 1000.0
        return 0.0

    def track_map_data(self):
        pts = self.track_pts
        cars = [(i, self.car_xy[i], self.cars[i]) for i in range(22)
                if self.cars[i].active and (self.car_xy[i][0] or self.car_xy[i][1])]
        xs = [p[0] for p in pts] + [c[1][0] for c in cars]
        zs = [p[1] for p in pts] + [c[1][1] for c in cars]
        if not xs:
            return pts, cars, None
        return pts, cars, (min(xs), min(zs), max(xs), max(zs))

    # -- derived strategy --------------------------------------------------
    def ers_pct(self):
        return max(0.0, min(100.0, self.ers_store / spec.ERS_MAX_JOULES * 100.0))

    def laps_remaining(self):
        if self.total_laps and self.current_lap:
            return max(0, self.total_laps - self.current_lap)
        return None

    def avg_tyre_wear(self):
        return sum(self.tyre_wear) / 4.0 if self.tyre_wear else 0.0

    def max_tyre_wear(self):
        return max(self.tyre_wear) if self.tyre_wear else 0.0

    def fuel_delta_laps(self):
        """Surplus(+)/deficit(-) of fuel in laps vs. laps remaining in race."""
        lr = self.laps_remaining()
        if lr is None:
            return None
        return self.fuel_remaining_laps - lr

    def tyre_life_left(self, cliff=85.0):
        """Estimated laps until average wear reaches the cliff threshold."""
        if self.wear_per_lap <= 0:
            return None
        cur = self.avg_tyre_wear()
        if cur >= cliff:
            return 0
        return (cliff - cur) / self.wear_per_lap

    def suggested_pit_lap(self, cliff=85.0):
        life = self.tyre_life_left(cliff)
        if life is None:
            return None
        return self.current_lap + int(life)

    def is_race(self):
        return self.session_type in (15, 16, 17, 10, 11, 12)

    def track_name(self):
        return spec.TRACKS.get(self.track_id, "Неизвестная трасса")
