"""Unit tests on hand-made inputs. Synthetic data here only checks the code, never the findings.

AI disclosure: this file was generated with the assistance of Claude (Anthropic), a generative AI
model, as part of the Dunkelflaute Explorer for NASA Space Apps 2026. The team directed the work and
reviewed and tested the code.
"""
import numpy as np
import pandas as pd

from dfx import capacity, config, events, stats
from dfx.panel import Panel

__ai_generated__ = True
__ai_tool__ = "Claude (Anthropic)"
__ai_disclosure__ = "Code generated with AI assistance; directed, reviewed and tested by the team."


def test_power_curve_bounds():
    t = config.TURBINES["default"]
    v = np.array([0, 2.9, 3, 12, 20, 25, 30])
    p = capacity.power_curve(v, t)
    assert p[0] == 0 and p[1] == 0 and p[3] == 1 and p[4] == 1 and p[5] == 0 and p[6] == 0


def test_daily_wind_cf_monotone_at_low_speed():
    cf = capacity.wind_cf(np.array([2, 4, 6, 8]))
    assert np.all(np.diff(cf) > 0)


def test_detect_events_runs():
    idx = pd.date_range("2000-01-01", periods=10)
    cf = pd.Series([0.5, 0.1, 0.1, 0.5, 0.1, 0.5, 0.1, 0.1, 0.1, 0.5], index=idx)
    ev = events.detect_events(cf, 0.2, 2)
    assert list(ev["length"]) == [2, 3]
    assert np.isclose(ev["severity"].iloc[0], 0.2)


def test_season_year_winter():
    d = pd.to_datetime(["2016-11-05", "2017-01-10", "2017-02-28", "2017-06-01"])
    sy = events.season_year(d, "winter").values
    assert sy[0] == 2017 and sy[1] == 2017 and sy[2] == 2017 and np.isnan(sy[3])


def test_trend_detects_slope():
    y = pd.Series(np.arange(40) * 0.5 + np.random.default_rng(0).normal(0, 1, 40), index=range(1985, 2025))
    t = stats.trend(y)
    assert t["significant"] and 4 < t["slope_decade"] < 6


def test_fdr():
    assert list(stats.bh_fdr(np.array([0.001, 0.02, 0.5]))) == [True, True, False]


def _synthetic_long(seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1984-01-01", "2025-12-31")
    rows = []
    for lat in (50.5, 51.5):
        for lon in (9.0, 10.0):
            doy = dates.dayofyear.values
            ghi = 2.8 + 2.4 * np.cos((doy - 172) / 365 * 2 * np.pi) + rng.normal(0, 0.6, len(dates))
            wind = np.clip(7 + 1.5 * np.cos((doy - 15) / 365 * 2 * np.pi) + rng.gamma(2, 1.2, len(dates)) - 2.4, 0.3, None)
            rows.append(pd.DataFrame({"date": dates, "lat": lat, "lon": lon, "wind_50m": wind, "wind_10m": wind * 0.8,
                                      "ghi": np.clip(ghi, 0.1, None), "t2m": 9 + rng.normal(0, 5, len(dates)),
                                      "ps": 100 + rng.normal(0, 1, len(dates)), "cloud": 60 + rng.normal(0, 15, len(dates))}))
    return pd.concat(rows)


def test_end_to_end_synthetic():
    from dfx import analysis
    p = Panel(_synthetic_long())
    d = config.Definition()
    ev, m, thr = events.run(p.regional_cf(d), d)
    assert len(m) == 41 and thr > 0
    h = analysis.headline(m)
    assert "slope_decade" in h
    tab, att, _ = analysis.drivers_and_attribution(p, d, n_boot=50)
    assert set(att.index) == {"wind_hub", "ghi"}
    r = analysis.robustness(p, d)
    assert len(r) >= 9
