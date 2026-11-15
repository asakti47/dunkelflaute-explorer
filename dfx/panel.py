"""Load the gridded daily data and build regional series: capacity factors, drivers, counterfactuals."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import capacity, config, events

DATA = Path(__file__).resolve().parent.parent / "data"
VARS = list(config.POWER_PARAMS.values())


class Panel:
    """Daily values on a dates x grid-points layout, one DataFrame per variable."""

    def __init__(self, long: pd.DataFrame):
        long = long.copy()
        long["date"] = pd.to_datetime(long["date"])
        long["pid"] = long["lat"].map("{:.1f}".format) + "_" + long["lon"].map("{:.1f}".format)
        self.points = (long[["pid", "lat", "lon"]].drop_duplicates("pid").set_index("pid").sort_index())
        self.v = {var: long.pivot(index="date", columns="pid", values=var)[self.points.index]
                  for var in VARS if var in long}
        self.dates = self.v["wind_50m"].index

    @classmethod
    def load(cls, folder: Path | str = DATA) -> "Panel":
        """Read the wide files data/power_<var>.csv.gz (rows = dates, columns = 'lat_lon' grid points)."""
        folder = Path(folder)
        if not (folder / "power_wind_50m.csv.gz").exists() and list(folder.glob("*.b64part*")):
            _assemble(folder)
        frames = []
        for var in VARS:
            f = folder / f"power_{var}.csv.gz"
            if not f.exists():
                continue
            w = pd.read_csv(f, index_col=0)
            w.index = pd.to_datetime(w.index.astype(str), format="%Y%m%d")
            w = w.replace(-999.0, np.nan)
            frames.append(w.stack(future_stack=True).rename(var))
        long = pd.concat(frames, axis=1).reset_index()
        long.columns = ["date", "pid"] + list(long.columns[2:])
        latlon = long["pid"].str.split("_", expand=True).astype(float)
        long["lat"], long["lon"] = latlon[0], latlon[1]
        return cls(long.drop(columns="pid"))

    # ------------------------------------------------------------ capacity factors
    def point_cf(self, d: config.Definition, wind_factor=None, ghi_factor=None) -> pd.DataFrame:
        w = self.v["wind_50m"].values
        g = self.v["ghi"].values
        if wind_factor is not None:
            w = w * np.asarray(wind_factor)[:, None]
        if ghi_factor is not None:
            g = g * np.asarray(ghi_factor)[:, None]
        cf = capacity.combined_cf(w, g, d.wind_share, d.turbine)
        return pd.DataFrame(cf, index=self.dates, columns=self.points.index)

    def regional_cf(self, d: config.Definition, wind_factor=None, ghi_factor=None) -> pd.Series:
        return self.point_cf(d, wind_factor, ghi_factor).mean(axis=1).rename("cf")

    # ------------------------------------------------------------ drivers
    def regional_daily(self) -> pd.DataFrame:
        out = pd.DataFrame({
            "wind_hub": capacity.hub_wind(self.v["wind_50m"].values).mean(axis=1),
            "ghi": self.v["ghi"].mean(axis=1).values,
            "cloud": self.v["cloud"].mean(axis=1).values,
            "t2m": self.v["t2m"].mean(axis=1).values,
            "ps": self.v["ps"].mean(axis=1).values,
        }, index=self.dates)
        # high-pressure day: regional pressure more than 1 baseline SD above its calendar-day normal
        doy = np.minimum(out.index.dayofyear.values, 365)
        base = (out.index.year >= config.BASELINE[0]) & (out.index.year <= config.BASELINE[1])
        clim = out["ps"][base].groupby(doy[base]).mean()
        clim = clim.rolling(31, center=True, min_periods=1).mean()
        anom = out["ps"].values - clim.reindex(doy).values
        sd = np.nanstd(anom[base])
        out["high_pressure"] = (anom > sd).astype(float)
        return out

    def drivers(self, season: str, nao: pd.Series | None = None) -> pd.DataFrame:
        daily = self.regional_daily()
        sy = events.season_year(daily.index, season)
        g = daily.groupby(sy.values)
        out = pd.DataFrame({
            "wind_hub": g["wind_hub"].mean(),
            "ghi": g["ghi"].mean(),
            "cloud": g["cloud"].mean(),
            "high_pressure_days": g["high_pressure"].sum(),
            "t2m": g["t2m"].mean(),
        })
        out.index = out.index.astype(int)
        out = out.reindex(events.valid_years(season))
        if nao is not None:
            out["nao"] = nao.reindex(out.index)
        out.index.name = "year"
        return out


def _assemble(folder: Path) -> None:
    """Rebuild power_<var>.csv.gz from base64 parts (how the data were moved into the repo)."""
    import base64
    import re
    from collections import defaultdict
    groups = defaultdict(list)
    for p in folder.glob("*.b64part*"):
        m = re.match(r"(.+)\.b64part(\d+)$", p.name)
        groups[m.group(1)].append((int(m.group(2)), p))
    for name, parts in groups.items():
        text = "".join(p.read_text().strip() for _, p in sorted(parts))
        try:
            (folder / name).write_bytes(base64.b64decode(text))
        except OSError:   # read-only deploy: decode to a temp folder instead
            import tempfile
            tmp = Path(tempfile.gettempdir()) / "dfx_data"
            tmp.mkdir(exist_ok=True)
            (tmp / name).write_bytes(base64.b64decode(text))


DRIVER_LABELS = {
    "wind_hub": ("Wind speed at 100 m", "m/s"),
    "ghi": ("Surface solar irradiance", "kWh/m²/day"),
    "cloud": ("Cloud cover", "%"),
    "high_pressure_days": ("High-pressure days", "days"),
    "t2m": ("Temperature (2 m)", "°C"),
    "nao": ("NAO index", "index"),
}
DIRECT_DRIVERS = ["wind_hub", "ghi"]   # enter the capacity factor directly: counterfactual possible


def detrend_factor(series_daily: pd.Series, season: str) -> np.ndarray:
    """Multiplicative factor that removes the linear trend in a driver's season-year mean.

    Returns one factor per day. Days outside the season keep factor 1. The series keeps its average level.
    """
    sy = events.season_year(series_daily.index, season)
    means = series_daily.groupby(sy.values).mean()
    means = means[means.index.isin(events.valid_years(season))]
    yrs = means.index.values.astype(float)
    b, a = np.polyfit(yrs, means.values, 1)
    fit = a + b * yrs
    level = fit.mean()
    fac_by_year = pd.Series(level / fit, index=means.index.astype(int))
    fac = sy.map(fac_by_year).fillna(1.0).values
    return fac
