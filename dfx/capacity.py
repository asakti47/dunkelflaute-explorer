"""Turn weather into potential power output with frozen technology (the fixed-fleet capacity factor).

The same turbine and the same solar panel are applied to every day from 1984 to 2025, so any trend
in the result comes from the weather, not from changes in the real power fleet.

AI disclosure: this file was generated with the assistance of Claude (Anthropic), a generative AI
model, as part of the Dunkelflaute Explorer for NASA Space Apps 2026. The team directed the work and
reviewed and tested the code.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from . import config
from .config import Turbine

__ai_generated__ = True
__ai_tool__ = "Claude (Anthropic)"
__ai_disclosure__ = "Code generated with AI assistance; directed, reviewed and tested by the team."

_Z = np.linspace(-2.5, 2.5, 51)                  # standard-normal grid for intra-day spread
_W = np.exp(-0.5 * _Z ** 2)
_W = _W / _W.sum()


def power_curve(v: np.ndarray, t: Turbine) -> np.ndarray:
    """Instantaneous output as a share of rated power (0-1)."""
    v = np.asarray(v, dtype=float)
    out = np.where((v >= t.cut_in) & (v < t.rated),
                   (v ** 3 - t.cut_in ** 3) / (t.rated ** 3 - t.cut_in ** 3), 0.0)
    out = np.where((v >= t.rated) & (v < t.cut_out), 1.0, out)
    return out


@lru_cache(maxsize=16)
def _daily_lookup(turbine_key: str, cv: float):
    """Expected daily capacity factor for a given daily-mean hub-height wind speed.

    A daily mean hides hour-to-hour swings, and the power curve is non-linear, so we average the curve
    over an assumed normal spread of hourly speeds around the daily mean (sd = cv x mean).
    """
    t = config.TURBINES[turbine_key]
    mu = np.arange(0, 40.01, 0.05)
    v = np.clip(mu[:, None] * (1 + cv * _Z[None, :]), 0, None)
    cf = (power_curve(v, t) * _W[None, :]).sum(axis=1)
    return mu, cf


def wind_cf(wind_50m: np.ndarray, turbine_key: str = "default",
            cv: float = config.INTRADAY_CV) -> np.ndarray:
    t = config.TURBINES[turbine_key]
    v_hub = np.asarray(wind_50m, dtype=float) * (t.hub_height / 50.0) ** config.SHEAR_ALPHA
    mu, cf = _daily_lookup(turbine_key, cv)
    return np.interp(v_hub, mu, cf)


def hub_wind(wind_50m: np.ndarray, turbine_key: str = "default") -> np.ndarray:
    t = config.TURBINES[turbine_key]
    return np.asarray(wind_50m, dtype=float) * (t.hub_height / 50.0) ** config.SHEAR_ALPHA


def solar_cf(ghi_kwh_day: np.ndarray, pr: float = config.PV_PERFORMANCE_RATIO) -> np.ndarray:
    """Daily solar capacity factor: daily irradiance over 24 h at 1 kW/m2 rating, times system losses."""
    return np.asarray(ghi_kwh_day, dtype=float) / 24.0 * pr


def combined_cf(wind_50m, ghi, wind_share: float = 0.5, turbine_key: str = "default") -> np.ndarray:
    return wind_share * wind_cf(wind_50m, turbine_key) + (1 - wind_share) * solar_cf(ghi)
