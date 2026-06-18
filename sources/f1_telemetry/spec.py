"""Statics for the F1 25 / 2026 Season Pack UDP spec: id->name lookups."""

# --- Packet ids -----------------------------------------------------------
PACKET_MOTION = 0
PACKET_SESSION = 1
PACKET_LAP_DATA = 2
PACKET_EVENT = 3
PACKET_PARTICIPANTS = 4
PACKET_CAR_SETUPS = 5
PACKET_CAR_TELEMETRY = 6
PACKET_CAR_STATUS = 7
PACKET_FINAL_CLASSIFICATION = 8
PACKET_LOBBY_INFO = 9
PACKET_CAR_DAMAGE = 10
PACKET_SESSION_HISTORY = 11
PACKET_TYRE_SETS = 12
PACKET_MOTION_EX = 13
PACKET_TIME_TRIAL = 14
PACKET_LAP_POSITIONS = 15

# --- Tracks ---------------------------------------------------------------
TRACKS = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Sakhir (Bahrain)",
    4: "Catalunya", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
    8: "Hockenheim", 9: "Hungaroring", 10: "Spa", 11: "Monza",
    12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "Texas (COTA)",
    16: "Brazil (Interlagos)", 17: "Austria (Red Bull Ring)", 18: "Sochi",
    19: "Mexico", 20: "Baku", 21: "Sakhir Short", 22: "Silverstone Short",
    23: "Texas Short", 24: "Suzuka Short", 25: "Hanoi", 26: "Zandvoort",
    27: "Imola", 28: "Portimao", 29: "Jeddah", 30: "Miami",
    31: "Las Vegas", 32: "Losail (Qatar)",
}

# --- Session types --------------------------------------------------------
SESSION_TYPES = {
    0: "Unknown", 1: "Practice 1", 2: "Practice 2", 3: "Practice 3",
    4: "Short Practice", 5: "Qualifying 1", 6: "Qualifying 2",
    7: "Qualifying 3", 8: "Short Qualifying", 9: "One-Shot Qualifying",
    10: "Sprint Shootout 1", 11: "Sprint Shootout 2", 12: "Sprint Shootout 3",
    13: "Short Sprint Shootout", 14: "One-Shot Sprint Shootout",
    15: "Race", 16: "Race 2", 17: "Race 3", 18: "Time Trial",
}

# --- Weather --------------------------------------------------------------
WEATHER = {
    0: "Clear", 1: "Light Cloud", 2: "Overcast",
    3: "Light Rain", 4: "Heavy Rain", 5: "Storm",
}
WEATHER_RU = {
    0: "Ясно", 1: "Облачно", 2: "Пасмурно",
    3: "Лёгкий дождь", 4: "Ливень", 5: "Гроза",
}

# --- Tyres ----------------------------------------------------------------
# Visual compounds (broadcast colours)
VISUAL_COMPOUND = {
    16: "Soft", 17: "Medium", 18: "Hard", 7: "Inter", 8: "Wet",
    15: "Wet (Classic)", 19: "Super Soft", 20: "Soft", 21: "Medium", 22: "Hard",
}
VISUAL_COMPOUND_SHORT = {
    16: "S", 17: "M", 18: "H", 7: "I", 8: "W",
    15: "W", 19: "SS", 20: "S", 21: "M", 22: "H",
}
# Actual compounds (real C-rating)
ACTUAL_COMPOUND = {
    16: "C5", 17: "C4", 18: "C3", 19: "C2", 20: "C1", 21: "C0",
    7: "Inter", 8: "Wet",
}
# Colour per visual compound for the UI
COMPOUND_COLOR = {
    16: "#ff3b3b",  # soft - red
    17: "#ffd23b",  # medium - yellow
    18: "#f0f0f0",  # hard - white
    7:  "#3bd16f",  # inter - green
    8:  "#3b8bff",  # wet - blue
}


def compound_color(visual):
    return COMPOUND_COLOR.get(visual, "#999999")


def compound_short(visual):
    return VISUAL_COMPOUND_SHORT.get(visual, "?")


# --- Teams ----------------------------------------------------------------
TEAMS = {
    0: "Mercedes", 1: "Ferrari", 2: "Red Bull Racing", 3: "Williams",
    4: "Aston Martin", 5: "Alpine", 6: "RB", 7: "Haas",
    8: "McLaren", 9: "Sauber",
    # classic / extra slots vary by title; fall back to generic name otherwise
}
TEAM_COLOR = {
    0: "#00d2be", 1: "#e8002d", 2: "#3671c6", 3: "#64c4ff",
    4: "#229971", 5: "#0093cc", 6: "#6692ff", 7: "#b6babd",
    8: "#ff8000", 9: "#52e252",
}


def team_color(team_id):
    return TEAM_COLOR.get(team_id, "#cccccc")


def team_name(team_id):
    return TEAMS.get(team_id, f"Team {team_id}")


# --- Surface types (for tyre contact) -------------------------------------
SURFACE = {
    0: "Tarmac", 1: "Rumble", 2: "Concrete", 3: "Rock", 4: "Gravel",
    5: "Mud", 6: "Sand", 7: "Grass", 8: "Water", 9: "Cobble",
    10: "Metal", 11: "Ridged",
}

# --- Flags ----------------------------------------------------------------
FIA_FLAGS = {-1: "", 0: "", 1: "GREEN", 2: "BLUE", 3: "YELLOW", 4: "RED"}
FLAG_COLOR = {
    "GREEN": "#3bd16f", "BLUE": "#3b8bff", "YELLOW": "#ffd23b", "RED": "#e8002d",
}

# --- Safety car -----------------------------------------------------------
SAFETY_CAR = {0: "", 1: "SAFETY CAR", 2: "VIRTUAL SC", 3: "FORMATION LAP"}

# --- ERS deploy modes -----------------------------------------------------
ERS_MODE = {0: "None", 1: "Medium", 2: "Hotlap", 3: "Overtake"}
ERS_MODE_RU = {0: "Нет", 1: "Средний", 2: "Хотлап", 3: "Обгон"}

# --- Fuel mix -------------------------------------------------------------
FUEL_MIX = {0: "Lean", 1: "Standard", 2: "Rich", 3: "Max"}
FUEL_MIX_RU = {0: "Экономь", 1: "Стандарт", 2: "Богатая", 3: "Макс"}

# --- Pit status -----------------------------------------------------------
PIT_STATUS = {0: "", 1: "PITTING", 2: "IN PIT"}

# --- Driver / result status ----------------------------------------------
DRIVER_STATUS = {
    0: "In garage", 1: "Flying lap", 2: "In lap", 3: "Out lap", 4: "On track",
}
RESULT_STATUS = {
    0: "Invalid", 1: "Inactive", 2: "Active", 3: "Finished",
    4: "DNF", 5: "DSQ", 6: "Not classified", 7: "Retired",
}

# Max ERS energy store in joules (full hybrid battery)
ERS_MAX_JOULES = 4_000_000.0


def fmt_laptime_ms(ms):
    """Format a lap/sector time in milliseconds to M:SS.mmm."""
    if not ms or ms <= 0:
        return "--:--.---"
    total = ms / 1000.0
    m = int(total // 60)
    s = total - m * 60
    if m > 0:
        return f"{m}:{s:06.3f}"
    return f"{s:.3f}"


def fmt_gap(ms):
    """Format a gap in milliseconds to +S.s."""
    if ms is None:
        return "--"
    if ms <= 0:
        return "--"
    s = ms / 1000.0
    if s >= 60:
        m = int(s // 60)
        return f"+{m}:{s - m * 60:06.3f}"
    return f"+{s:.3f}"
