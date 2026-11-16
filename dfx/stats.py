"""Trend tests, period comparison, attribution and the bootstrap.

AI disclosure: this file was generated with the assistance of Claude (Anthropic), a generative AI
model, as part of the Dunkelflaute Explorer for NASA Space Apps 2026. The team directed the work and
reviewed and tested the code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pymannkendall as mk
import statsmodels.api as sm
from scipy import stats

from . import config

__ai_generated__ = True
__ai_tool__ = "Claude (Anthropic)"
__ai_disclosure__ = "Code generated with AI assistance; directed, reviewed and tested by the team."


def _clean(y: pd.Series) -> pd.Series:
    y = pd.Series(y).astype(float)
    return y[np.isfinite(y.values)]


def trend(y: pd.Series, alpha: float = 0.05) -> dict:
    """Mann-Kendall (original and autocorrelation-corrected) with Sen's slope per decade and its 95% CI."""
    y = _clean(y)
    yrs = y.index.values.astype(float)
    out = {"n": len(y)}
    if len(y) < 8 or np.nanstd(y.values) == 0:
        return out | {"slope_decade": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_mk": 1.0,
                      "intercept": float(np.nanmean(y.values)) if len(y) else 0.0,
                      "p_mk_mod": 1.0, "tau": 0.0, "significant": False, "direction": "no trend"}
    r0 = mk.original_test(y.values)
    try:
        r1 = mk.hamed_rao_modification_test(y.values)
        p_mod = float(r1.p)
    except Exception:  # noqa: BLE001 - very short or flat series
        p_mod = float(r0.p)
    ts = stats.theilslopes(y.values, yrs, alpha=1 - alpha)
    slope = ts.slope * 10
    out |= {
        "slope_decade": float(slope),
        "ci_low": float(ts.low_slope * 10), "ci_high": float(ts.high_slope * 10),
        "intercept": float(ts.intercept),
        "p_mk": float(r0.p), "p_mk_mod": p_mod, "tau": float(r0.Tau),
        "significant": bool(p_mod < alpha),
        "direction": "rising" if r0.Tau > 0 else ("falling" if r0.Tau < 0 else "no trend"),
    }
    return out


def ols_trend(y: pd.Series) -> dict:
    y = _clean(y)
    res = stats.linregress(y.index.values.astype(float), y.values)
    return {"slope_decade": res.slope * 10, "p": res.pvalue, "intercept": res.intercept}


def period_compare(y: pd.Series) -> dict:
    y = _clean(y)
    b = y[(y.index >= config.BASELINE[0]) & (y.index <= config.BASELINE[1])]
    r = y[(y.index >= config.RECENT[0]) & (y.index <= config.RECENT[1])]
    p = float(stats.mannwhitneyu(r.values, b.values, alternative="two-sided").pvalue) if len(b) and len(r) else np.nan
    return {"baseline_mean": float(b.mean()), "recent_mean": float(r.mean()),
            "ratio": float(r.mean() / b.mean()) if b.mean() else np.nan, "p_mannwhitney": p}


def poisson_trend(counts: pd.Series) -> dict:
    y = _clean(counts)
    X = sm.add_constant((y.index.values.astype(float) - y.index.min()) / 10)
    try:
        m = sm.GLM(y.values, X, family=sm.families.Poisson()).fit()
        return {"rate_ratio_decade": float(np.exp(m.params[1])), "p": float(m.pvalues[1])}
    except Exception:  # noqa: BLE001
        return {"rate_ratio_decade": np.nan, "p": np.nan}


def pettitt(y: pd.Series) -> dict:
    """Pettitt test for a single abrupt shift. Returns the first year of the new regime."""
    y = _clean(y)
    x = y.values
    n = len(x)
    if n < 8:
        return {"change_year": None, "p": 1.0}
    s = np.sign(x[:, None] - x[None, :])
    u = np.array([s[: t + 1, t + 1:].sum() for t in range(n - 1)])
    k = np.abs(u).max()
    t = int(np.abs(u).argmax())
    p = float(min(1.0, 2 * np.exp(-6 * k ** 2 / (n ** 3 + n ** 2))))
    return {"change_year": int(y.index[t + 1]), "p": p}


def nao_controlled_trend(y: pd.Series, nao: pd.Series) -> dict:
    df = pd.concat([_clean(y).rename("y"), nao.rename("nao")], axis=1).dropna()
    if len(df) < 10:
        return {"slope_decade": np.nan, "p": np.nan}
    X = sm.add_constant(np.column_stack([(df.index.values - df.index.min()) / 10, df["nao"].values]))
    m = sm.OLS(df["y"].values, X).fit()
    return {"slope_decade": float(m.params[1]), "p": float(m.pvalues[1]),
            "nao_coef": float(m.params[2]), "nao_p": float(m.pvalues[2])}


def _detrend(s: pd.Series) -> pd.Series:
    s = _clean(s)
    b, a = np.polyfit(s.index.values.astype(float), s.values, 1)
    return s - (a + b * s.index.values)


def sensitivity(y: pd.Series, x: pd.Series) -> dict:
    """Year-to-year link between a driver and Dunkelflaute, with both series detrended first."""
    df = pd.concat([_detrend(y).rename("y"), _detrend(x).rename("x")], axis=1).dropna()
    res = stats.linregress(df["x"].values, df["y"].values)
    return {"slope": float(res.slope), "p": float(res.pvalue), "r": float(res.rvalue)}


def bh_fdr(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg: True where the test survives false-discovery-rate control."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    passed = np.zeros(n, dtype=bool)
    below = np.flatnonzero(ranked <= q)
    if len(below):
        passed[order[: below.max() + 1]] = True
    return passed


def holm(p: dict) -> dict:
    items = sorted(p.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, v) in enumerate(items):
        running = max(running, min(1.0, (m - i) * v))
        out[k] = running
    return out


def _slope(yrs: np.ndarray, y: np.ndarray) -> float:
    yrs = yrs - yrs.mean()
    return float((yrs * (y - y.mean())).sum() / (yrs ** 2).sum())


def bootstrap_share(actual: pd.Series, counterfactual: pd.Series, n: int = 1000,
                    block: int = 5, seed: int = 42, driver: pd.Series | None = None) -> dict:
    """Share of the trend explained by a driver, with a moving-block bootstrap 95% range.

    Years are resampled in blocks with their labels kept, and the actual and counterfactual series are
    resampled together (paired), so shared weather noise cancels. When the driver's own yearly series is given,
    each resample also re-estimates the driver's trend and scales the effect by it, so uncertainty in whether
    the driver is really trending is carried into the range (first-order approximation).
    """
    parts = [actual.rename("a"), counterfactual.rename("c")]
    if driver is not None:
        parts.append(driver.rename("d"))
    df = pd.concat(parts, axis=1).dropna()
    yrs = df.index.values.astype(float)
    a, c = df["a"].values, df["c"].values
    s_a, s_c = _slope(yrs, a), _slope(yrs, c)
    share = 1 - s_c / s_a if s_a else np.nan
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(df) / block))
    starts = np.arange(len(df) - block + 1)
    shares, reductions = [], []
    d = df["d"].values if driver is not None else None
    b_hat = _slope(yrs, d) if d is not None else None
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, nb)])[: len(df)]
        sa, sc = _slope(yrs[idx], a[idx]), _slope(yrs[idx], c[idx])
        scale = _slope(yrs[idx], d[idx]) / b_hat if d is not None and b_hat else 1.0
        sc = sa - (sa - sc) * scale
        reductions.append((sa - sc) * 10)
        if sa != 0:
            shares.append(1 - sc / sa)
    lo, hi = np.percentile(shares, [2.5, 97.5]) if shares else (np.nan, np.nan)
    rlo, rhi = np.percentile(reductions, [2.5, 97.5])
    return {"share": float(share), "share_low": float(lo), "share_high": float(hi),
            "reduction_decade": float((s_a - s_c) * 10), "reduction_low": float(rlo),
            "reduction_high": float(rhi), "slope_actual_decade": s_a * 10,
            "slope_cf_decade": s_c * 10, "significant": bool(rlo > 0 or rhi < 0),
            "p_boot": float(min(1.0, 2 * min(np.mean(np.array(reductions) <= 0),
                                             np.mean(np.array(reductions) >= 0))))}
