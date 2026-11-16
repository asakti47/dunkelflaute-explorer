"""Detect Dunkelflaute events in a daily capacity-factor series and summarise them per year or winter.

AI disclosure: this file was generated with the assistance of Claude (Anthropic), a generative AI
model, as part of the Dunkelflaute Explorer for NASA Space Apps 2026. The team directed the work and
reviewed and tested the code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

__ai_generated__ = True
__ai_tool__ = "Claude (Anthropic)"
__ai_disclosure__ = "Code generated with AI assistance; directed, reviewed and tested by the team."

METRICS = {
    "count": "Event count (events)",
    "mean_len": "Mean event length (days)",
    "max_len": "Longest event (days)",
    "total_days": "Total Dunkelflaute days",
    "severity": "Severity (CF shortfall x days)",
}


def season_year(dates: pd.DatetimeIndex, season: str) -> pd.Series:
    """Map each date to its season-year. Winter = Nov-Feb, labelled by the January year."""
    dates = pd.DatetimeIndex(dates)
    if season == "year":
        return pd.Series(dates.year, index=dates, dtype="float")
    m = dates.month
    y = np.where(m >= 11, dates.year + 1, dates.year).astype(float)
    y = np.where(np.isin(m, [11, 12, 1, 2]), y, np.nan)
    return pd.Series(y, index=dates)


def valid_years(season: str) -> list[int]:
    first = int(config.START[:4])
    last = int(config.END[:4])
    return list(range(first + 1, last + 1)) if season == "winter" else list(range(first, last + 1))


def baseline_threshold(cf: pd.Series, pct: float) -> float:
    b = cf[(cf.index.year >= config.BASELINE[0]) & (cf.index.year <= config.BASELINE[1])]
    return float(np.nanpercentile(b.values, pct))


def detect_events(cf: pd.Series, threshold: float, min_days: int) -> pd.DataFrame:
    """Runs of consecutive days below the threshold lasting at least min_days."""
    low = (cf.values < threshold) & ~np.isnan(cf.values)
    idx = np.flatnonzero(np.diff(np.concatenate(([0], low.astype(int), [0]))))
    starts, ends = idx[0::2], idx[1::2]          # end is exclusive
    keep = (ends - starts) >= min_days
    rows = []
    for s, e in zip(starts[keep], ends[keep]):
        seg = cf.values[s:e]
        rows.append({
            "start": cf.index[s], "end": cf.index[e - 1], "length": int(e - s),
            "severity": float(np.sum(threshold - seg)), "min_cf": float(np.min(seg)),
        })
    return pd.DataFrame(rows, columns=["start", "end", "length", "severity", "min_cf"])


def yearly_metrics(events: pd.DataFrame, season: str) -> pd.DataFrame:
    """One row per season-year with the five metrics; years without events get zeros."""
    years = valid_years(season)
    out = pd.DataFrame(index=pd.Index(years, name="year"))
    if len(events):
        sy = season_year(pd.DatetimeIndex(events["start"]), season).values
        ev = events.assign(sy=sy).dropna(subset=["sy"])
        g = ev.groupby("sy")
        out["count"] = g.size()
        out["mean_len"] = g["length"].mean()
        out["max_len"] = g["length"].max()
        out["total_days"] = g["length"].sum()
        out["severity"] = g["severity"].sum()
    for c in METRICS:
        if c not in out:
            out[c] = np.nan
    out[["count", "max_len", "total_days", "severity"]] = out[["count", "max_len", "total_days", "severity"]].fillna(0)
    return out[list(METRICS)]


def run(cf: pd.Series, d: config.Definition) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    thr = baseline_threshold(cf, d.threshold_pct)
    ev = detect_events(cf, thr, d.min_days)
    return ev, yearly_metrics(ev, d.season), thr
