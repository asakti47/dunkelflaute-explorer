"""Download daily NASA POWER data (MERRA-2 meteorology + CERES/SRB solar) for a grid of points."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import requests

from . import config

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def fetch_point(lat: float, lon: float, start: str = config.START, end: str = config.END,
                retries: int = 4) -> pd.DataFrame:
    """Return one row per day for a single location, columns named as in config.POWER_PARAMS."""
    params = {
        "parameters": ",".join(config.POWER_PARAMS),
        "community": "RE",
        "latitude": lat,
        "longitude": lon,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    for attempt in range(retries):
        try:
            r = requests.get(URL, params=params, timeout=120)
            r.raise_for_status()
            p = r.json()["properties"]["parameter"]
            break
        except Exception:  # noqa: BLE001 - retry any network hiccup
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    df = pd.DataFrame({config.POWER_PARAMS[k]: pd.Series(v) for k, v in p.items()})
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.replace(-999.0, np.nan)
    df.index.name = "date"
    df["lat"], df["lon"] = lat, lon
    return df.reset_index()


def fetch_grid(lats=config.LATS, lons=config.LONS, pause: float = 0.5) -> pd.DataFrame:
    frames = []
    for lat in lats:
        for lon in lons:
            frames.append(fetch_point(lat, lon))
            time.sleep(pause)   # be polite to the public API
    out = pd.concat(frames, ignore_index=True)
    floats = [c for c in out.columns if c not in ("date",)]
    out[floats] = out[floats].astype("float32")
    return out
