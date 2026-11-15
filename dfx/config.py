"""Central settings for the Dunkelflaute Explorer.

Every number that shapes the analysis lives here so it can be cited and changed in one place.
"""
from dataclasses import dataclass, field

# ---------------------------------------------------------------- region & period
# A 1-degree grid over Germany and its immediate surroundings.
LATS = [47.5 + i for i in range(8)]   # 47.5 .. 54.5 N
LONS = [6.0 + i for i in range(10)]   # 6.0 .. 15.0 E
REGION_NAME = "Germany and surroundings (47.5-54.5 N, 6-15 E)"

START = "19840101"   # first full year of NASA POWER solar data
END = "20251231"
BASELINE = (1984, 2013)   # fixed 30-year reference period
RECENT = (2014, 2025)     # compared against the baseline

# NASA POWER daily parameters (community RE)
POWER_PARAMS = {
    "WS50M": "wind_50m",          # m/s, MERRA-2
    "WS10M": "wind_10m",          # m/s, MERRA-2
    "ALLSKY_SFC_SW_DWN": "ghi",   # kWh/m2/day, CERES SYN1deg / GEWEX SRB
    "T2M": "t2m",                 # deg C, MERRA-2
    "PS": "ps",                   # kPa, MERRA-2 surface pressure
    "CLOUD_AMT": "cloud",         # %, CERES / ISCCP
}


# ---------------------------------------------------------------- frozen technology
@dataclass(frozen=True)
class Turbine:
    """A generic power curve: cubic from cut-in to rated, flat to cut-out."""
    name: str
    hub_height: float   # m
    cut_in: float       # m/s
    rated: float        # m/s
    cut_out: float      # m/s


TURBINES = {
    "default": Turbine("Reference 2020s turbine", 100.0, 3.0, 12.0, 25.0),
    "older": Turbine("Older 2000s turbine", 80.0, 4.0, 14.0, 25.0),
    "modern": Turbine("Modern low-wind turbine", 120.0, 3.0, 10.5, 25.0),
}

SHEAR_ALPHA = 1 / 7          # power-law exponent to move 50 m wind to hub height
INTRADAY_CV = 0.25           # assumed hour-to-hour spread of wind within a day (sd / mean)
PV_PERFORMANCE_RATIO = 0.80  # fixed solar panel system losses


# ---------------------------------------------------------------- event definition
@dataclass
class Definition:
    threshold_pct: float = 10.0   # percentile of baseline daily combined CF
    min_days: int = 2             # consecutive low days that make an event
    wind_share: float = 0.5       # wind/solar mix by capacity
    turbine: str = "default"
    season: str = "winter"        # "winter" (Nov-Feb) or "year"


DEFAULT = Definition()
