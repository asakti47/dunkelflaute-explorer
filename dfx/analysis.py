"""End-to-end analysis used by both the batch script and the dashboard."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, events, stats
from .panel import DIRECT_DRIVERS, DRIVER_LABELS, Panel, detrend_factor

DATA = Path(__file__).resolve().parent.parent / "data"


def load_nao(season: str) -> pd.Series | None:
    path = DATA / "nao_monthly.csv"
    if not path.exists():
        return None
    m = pd.read_csv(path)
    dates = pd.to_datetime(dict(year=m["year"], month=m["month"], day=1))
    s = pd.Series(m["nao"].values, index=dates)
    sy = events.season_year(s.index, season)
    out = s.groupby(sy.values).mean()
    out.index = out.index.astype(int)
    return out.rename("nao")


def headline(metrics: pd.DataFrame, nao: pd.Series | None = None) -> pd.DataFrame:
    rows = []
    for k, label in events.METRICS.items():
        y = metrics[k]
        t = stats.trend(y)
        pc = stats.period_compare(y)
        pt = stats.pettitt(y)
        row = {"metric": k, "label": label, **t, **{f"pc_{a}": b for a, b in pc.items()},
               "pettitt_year": pt["change_year"], "pettitt_p": pt["p"]}
        if k == "count":
            pr = stats.poisson_trend(y)
            row |= {"poisson_rate_ratio_decade": pr["rate_ratio_decade"], "poisson_p": pr["p"]}
        if nao is not None:
            nc = stats.nao_controlled_trend(y, nao)
            row |= {"nao_ctrl_slope_decade": nc["slope_decade"], "nao_ctrl_p": nc["p"]}
        rows.append(row)
    return pd.DataFrame(rows).set_index("metric")


def per_cell(panel: Panel, d: config.Definition, metric: str = "total_days") -> pd.DataFrame:
    cf = panel.point_cf(d)
    rows = []
    for pid in cf.columns:
        _, m, _ = events.run(cf[pid], d)
        t = stats.trend(m[metric])
        rows.append({"pid": pid, "lat": panel.points.loc[pid, "lat"], "lon": panel.points.loc[pid, "lon"],
                     "slope_decade": t["slope_decade"], "p": t["p_mk_mod"], "mean": m[metric].mean()})
    out = pd.DataFrame(rows)
    out["significant_fdr"] = stats.bh_fdr(out["p"].values)
    out["significant_raw"] = out["p"] < 0.05
    return out


def robustness(panel: Panel, base: config.Definition, metric: str = "total_days",
               nao: pd.Series | None = None) -> pd.DataFrame:
    rows = []
    variants = [("Default", base)]
    variants += [(f"Threshold {p:g}th pct", replace(base, threshold_pct=p)) for p in (5, 20)]
    variants += [(f"Min length {n} day{'s' if n > 1 else ''}", replace(base, min_days=n)) for n in (1, 3)]
    variants += [(config.TURBINES[k].name, replace(base, turbine=k)) for k in ("older", "modern")]
    variants += [("Wind-heavy mix (70/30)", replace(base, wind_share=0.7)),
                 ("Solar-heavy mix (30/70)", replace(base, wind_share=0.3))]
    for name, d in variants:
        _, m, thr = events.run(panel.regional_cf(d), d)
        t = stats.trend(m[metric])
        rows.append({"variant": name, "threshold_cf": thr, "mean": m[metric].mean(), **t})
    # meteorological index: wind AND irradiance both below their baseline 20th percentile
    daily = panel.regional_daily()
    for pct in (20,):
        wthr = events.baseline_threshold(daily["wind_hub"], pct)
        gthr = events.baseline_threshold(daily["ghi"], pct)
        low = ((daily["wind_hub"] < wthr) & (daily["ghi"] < gthr)).astype(float)
        idx = pd.Series(np.where(low.values > 0, 0.0, 1.0), index=daily.index)
        ev = events.detect_events(idx, 0.5, base.min_days)
        m = events.yearly_metrics(ev, base.season)
        t = stats.trend(m[metric])
        rows.append({"variant": f"Weather-only index (wind & sun < {pct}th pct)", "threshold_cf": np.nan,
                     "mean": m[metric].mean(), **t})
    if nao is not None:
        _, m, _ = events.run(panel.regional_cf(base), base)
        nc = stats.nao_controlled_trend(m[metric], nao)
        rows.append({"variant": "Default, controlling for NAO", "threshold_cf": np.nan, "mean": m[metric].mean(),
                     "slope_decade": nc["slope_decade"], "p_mk_mod": nc["p"],
                     "significant": bool(nc["p"] < 0.05), "direction": "rising" if nc["slope_decade"] > 0 else "falling"})
    return pd.DataFrame(rows)


def drivers_and_attribution(panel: Panel, d: config.Definition, metric: str = "total_days",
                            nao: pd.Series | None = None, n_boot: int = 1000):
    cf = panel.regional_cf(d)
    _, m, thr = events.run(cf, d)
    y = m[metric]
    drv = panel.drivers(d.season, nao)
    rows = []
    for k in drv.columns:
        t = stats.trend(drv[k])
        s = stats.sensitivity(y, drv[k])
        rows.append({"driver": k, "label": DRIVER_LABELS[k][0], "unit": DRIVER_LABELS[k][1],
                     "trend_decade": t["slope_decade"], "trend_low": t["ci_low"], "trend_high": t["ci_high"],
                     "trend_p": t["p_mk_mod"], "trend_significant": t["significant"],
                     "sens_slope": s["slope"], "sens_p": s["p"], "sens_r": s["r"],
                     "implied_contribution_decade": t["slope_decade"] * s["slope"]})
    tab = pd.DataFrame(rows).set_index("driver")

    # counterfactual: remove the long-term trend of each direct driver, recompute events
    daily = panel.regional_daily()
    att, cf_series = [], {}
    for k in DIRECT_DRIVERS:
        src = daily["wind_hub"] if k == "wind_hub" else daily["ghi"]
        fac = detrend_factor(src, d.season)
        kw = {"wind_factor": fac} if k == "wind_hub" else {"ghi_factor": fac}
        cf_k = panel.regional_cf(d, **kw)
        # same threshold as the actual run, so only the driver changes
        ev_k = events.detect_events(cf_k, thr, d.min_days)
        m_k = events.yearly_metrics(ev_k, d.season)
        cf_series[k] = m_k[metric]
        b = stats.bootstrap_share(y, m_k[metric], n=n_boot, driver=drv[k])
        att.append({"driver": k, "label": DRIVER_LABELS[k][0], **b})
    att = pd.DataFrame(att).set_index("driver")
    if len(att):
        adj = stats.holm(att["p_boot"].to_dict())
        att["p_holm"] = pd.Series(adj)
        att["significant_holm"] = att["p_holm"] < 0.05
    return tab, att, pd.DataFrame(cf_series).assign(actual=y)
