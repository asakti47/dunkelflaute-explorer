"""Dunkelflaute Explorer - NASA Space Apps 2026, Be An Earth System Trend Detective!

Run locally with:  streamlit run streamlit_app.py
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dfx import analysis, config, events, stats
from dfx.panel import DRIVER_LABELS, Panel, detrend_factor

st.set_page_config(page_title="Dunkelflaute Explorer", page_icon="🌥️", layout="wide")

BLUE, ORANGE, GREY, RED = "#2a6fdb", "#e8743b", "#8a8a8a", "#c0392b"
METRIC_LABELS = events.METRICS


# ------------------------------------------------------------------ cached computation
@st.cache_resource(show_spinner="Loading NASA POWER data...")
def load_panel() -> Panel:
    return Panel.load()


@st.cache_data(show_spinner=False)
def regional_daily() -> pd.DataFrame:
    return load_panel().regional_daily()


@st.cache_data(show_spinner=False)
def run_regional(d_key: tuple, detrend_wind: bool, detrend_ghi: bool):
    d = config.Definition(*d_key)
    p = load_panel()
    daily = regional_daily()
    cf = p.regional_cf(d)
    ev, m, thr = events.run(cf, d)
    cf_series = None
    if detrend_wind or detrend_ghi:
        wf = detrend_factor(daily["wind_hub"], d.season) if detrend_wind else None
        gf = detrend_factor(daily["ghi"], d.season) if detrend_ghi else None
        cf_c = p.regional_cf(d, wind_factor=wf, ghi_factor=gf)
        ev_c = events.detect_events(cf_c, thr, d.min_days)
        cf_series = events.yearly_metrics(ev_c, d.season)
    return cf, ev, m, thr, cf_series


@st.cache_data(show_spinner="Testing every grid cell...")
def run_cells(d_key: tuple, metric: str) -> pd.DataFrame:
    return analysis.per_cell(load_panel(), config.Definition(*d_key), metric)


@st.cache_data(show_spinner="Attributing the trend to its drivers...")
def run_drivers(d_key: tuple, metric: str):
    d = config.Definition(*d_key)
    nao = analysis.load_nao(d.season)
    return analysis.drivers_and_attribution(load_panel(), d, metric, nao=nao, n_boot=1000)


def key(d: config.Definition) -> tuple:
    return (d.threshold_pct, d.min_days, d.wind_share, d.turbine, d.season)


def fmt_s(x: float, nd: int = 2) -> str:
    x = 0.0 if abs(x) < 0.5 * 10 ** -nd else x
    return f"{x:+.{nd}f}"


def fmt_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


# ------------------------------------------------------------------ sidebar controls
st.sidebar.title("Controls")
if st.sidebar.button("Reset to default settings"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
season = st.sidebar.radio("Season", ["winter", "year"], format_func=lambda s: "Winter (Nov–Feb)" if s == "winter" else "Full year",
                          key="season", help="Dunkelflaute is mostly a winter problem: short days, low sun, calm high-pressure spells.")
st.sidebar.caption(f"Period: 1984–2025 · Baseline: {config.BASELINE[0]}–{config.BASELINE[1]}")
metric = st.sidebar.selectbox("Measure", list(METRIC_LABELS), index=3, format_func=METRIC_LABELS.get, key="metric")
thr = st.sidebar.slider("Low-output threshold (percentile of baseline days)", 5, 25, 10, 5, key="thr",
                        help="A day counts as 'low' if combined wind + solar output is below this percentile of all 1984–2013 days.")
min_days = st.sidebar.radio("Minimum event length", [1, 2, 3], index=1, horizontal=True, format_func=lambda n: f"{n} day{'s' if n > 1 else ''}", key="min_days")
mix = st.sidebar.slider("Wind share of the fleet", 0.0, 1.0, 0.5, 0.1, key="mix", help="Frozen mix of wind vs solar capacity.")
turbine = st.sidebar.selectbox("Turbine (frozen for all years)", list(config.TURBINES), format_func=lambda k: config.TURBINES[k].name, key="turbine")
st.sidebar.markdown("**Drivers** — switch one off to remove its long-term trend")
on_wind = st.sidebar.toggle("Wind speed", value=True, key="on_wind")
on_ghi = st.sidebar.toggle("Solar irradiance", value=True, key="on_ghi")
st.sidebar.caption("Off = that driver keeps its day-to-day weather but loses its 1984–2025 trend. "
                   "Cloud, pressure, temperature and NAO act *through* wind and sun; see 'Why is it changing?'.")

d = config.Definition(threshold_pct=float(thr), min_days=int(min_days), wind_share=float(mix), turbine=turbine, season=season)
cf, ev, m, thr_cf, cf_m = run_regional(key(d), not on_wind, not on_ghi)
y = m[metric]
t = stats.trend(y)
t_count = stats.trend(m["count"])
t_len = stats.trend(m["mean_len"])
pc = stats.period_compare(y)

# ------------------------------------------------------------------ header
st.title("🌥️ Dunkelflaute Explorer")
st.markdown(f"**Is the 'dark doldrums' — long spells with little wind *and* little sun — getting more frequent or longer over {config.REGION_NAME}, and why?**  \n"
            "Built on NASA POWER data (MERRA-2 wind, CERES/SRB sunlight), 1984–2025.")

tab_dash, tab_walk, tab_defs, tab_method = st.tabs(["📊 Dashboard", "🕵️ Detective walkthrough", "📖 Definitions", "🔬 Method & data"])

with tab_dash:
    # ---------------- verdict cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Frequency (events per season)", f"{fmt_s(t_count['slope_decade'])} / decade",
              f"{'significant' if t_count['significant'] else 'not significant'} · {fmt_p(t_count['p_mk_mod'])}",
              delta_color="off")
    c2.metric("Typical event length (days)", f"{fmt_s(t_len['slope_decade'])} / decade",
              f"{'significant' if t_len['significant'] else 'not significant'} · {fmt_p(t_len['p_mk_mod'])}",
              delta_color="off")
    cells = run_cells(key(d), metric)
    up = int(((cells["slope_decade"] > 0) & cells["significant_fdr"]).sum())
    down = int(((cells["slope_decade"] < 0) & cells["significant_fdr"]).sum())
    c3.metric("Where: significant cells", f"{up} ↑ · {down} ↓",
              f"of {len(cells)} grid cells (after FDR)", delta_color="off")
    drv_tab, att, cfs = run_drivers(key(d), metric)
    if len(att):
        sig = att[att["significant_holm"]]
        if len(sig):
            short = {"wind_hub": "Wind", "ghi": "Sun"}
            parts = [f"{short[k]} {fmt_s(r.reduction_decade, 1)}" for k, r in sig.iterrows()]
            c4.metric("Driver effects (significant)", " · ".join(parts),
                      f"{METRIC_LABELS[metric].split(' (')[0].lower()} per decade", delta_color="off")
        else:
            c4.metric("Driver effects", "None", "wind & sun trends: no significant effect", delta_color="off")

    # ---------------- time series
    st.subheader(f"{METRIC_LABELS[metric]} per {'winter' if season == 'winter' else 'year'}")
    yrs = y.index.values
    fig = go.Figure()
    fig.add_bar(x=yrs, y=y.values, name="Actual", marker_color=BLUE, opacity=0.55)
    if t.get("n", 0) >= 8:
        line = t["intercept"] + t["slope_decade"] / 10 * yrs
        fig.add_scatter(x=yrs, y=line, name=f"Trend {fmt_s(t['slope_decade'])}/decade ({fmt_p(t['p_mk_mod'])})",
                        line=dict(color="black", dash="dash"))
    roll = y.rolling(10, center=True, min_periods=5).mean()
    fig.add_scatter(x=yrs, y=roll.values, name="10-year average", line=dict(color=BLUE, width=3))
    if cf_m is not None:
        off = [n for n, on in (("wind", on_wind), ("sun", on_ghi)) if not on]
        yc = cf_m[metric]
        tc = stats.trend(yc)
        fig.add_scatter(x=yrs, y=yc.rolling(10, center=True, min_periods=5).mean().values,
                        name=f"10-yr avg, {' & '.join(off)} trend removed", line=dict(color=ORANGE, width=3))
        if tc.get("n", 0) >= 8:
            fig.add_scatter(x=yrs, y=tc["intercept"] + tc["slope_decade"] / 10 * yrs,
                            name=f"Trend without it {fmt_s(tc['slope_decade'])}/decade", line=dict(color=ORANGE, dash="dash"))
    base = config.BASELINE
    fig.add_vrect(x0=base[0] - 0.5, x1=base[1] + 0.5, fillcolor=GREY, opacity=0.08, line_width=0,
                  annotation_text="baseline", annotation_position="top left")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.15),
                      yaxis_title=METRIC_LABELS[metric], xaxis_title=None)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Recent ({config.RECENT[0]}–{config.RECENT[1]}) average {pc['recent_mean']:.2f} vs baseline {pc['baseline_mean']:.2f} "
               f"(ratio {pc['ratio']:.2f}, Mann-Whitney {fmt_p(pc['p_mannwhitney'])}). "
               f"Sen's slope 95% range: {fmt_s(t.get('ci_low', 0))} to {fmt_s(t.get('ci_high', 0))} per decade.")

    # ---------------- map + drivers
    left, right = st.columns(2)
    with left:
        st.subheader("Where is it changing?")
        cells = cells.copy()
        cells["label"] = np.where(cells["significant_fdr"], "significant", "not significant")
        lim = float(np.nanmax(np.abs(cells["slope_decade"]))) or 1.0
        grid = cells.pivot(index="lat", columns="lon", values="slope_decade")
        pv = cells.pivot(index="lat", columns="lon", values="p")
        mfig = go.Figure(go.Heatmap(z=grid.values, x=grid.columns, y=grid.index, colorscale="RdBu_r", zmin=-lim, zmax=lim,
                                    colorbar=dict(title="per decade"), customdata=pv.values, xgap=2, ygap=2,
                                    hovertemplate="%{y}°N %{x}°E<br>%{z:+.2f} per decade<br>p = %{customdata:.3f}<extra></extra>"))
        sig = cells[cells["significant_fdr"]]
        mfig.add_scatter(x=sig["lon"], y=sig["lat"], mode="markers", marker=dict(symbol="star", size=16, color="black"),
                         name="significant", hoverinfo="skip")
        for name, lat, lon in (("Hamburg", 53.55, 10.0), ("Berlin", 52.52, 13.4), ("Cologne", 50.94, 6.96), ("Munich", 48.14, 11.58)):
            mfig.add_annotation(x=lon, y=lat, text=name, showarrow=False, font=dict(size=11, color="#222"), bgcolor="rgba(255,255,255,0.6)")
        mfig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                           xaxis=dict(title="Longitude (°E)", dtick=1), yaxis=dict(title="Latitude (°N)", dtick=1, scaleanchor="x", scaleratio=1.5))
        st.plotly_chart(mfig, width="stretch")
        st.caption("Each square is a 1° grid cell. Red = rising, blue = falling. ★ = significant after false-discovery-rate correction.")
    with right:
        st.subheader("Why is it changing?")
        if len(att):
            bfig = go.Figure()
            bfig.add_bar(y=[DRIVER_LABELS[k][0] for k in att.index], x=att["reduction_decade"], orientation="h",
                         marker_color=[BLUE if s else GREY for s in att["significant_holm"]],
                         error_x=dict(type="data", symmetric=False,
                                      array=att["reduction_high"] - att["reduction_decade"],
                                      arrayminus=att["reduction_decade"] - att["reduction_low"]))
            bfig.add_vline(x=0, line_color="black")
            bfig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10),
                               xaxis_title=f"Trend explained ({METRIC_LABELS[metric].split('(')[-1].rstrip(')')} per decade)")
            st.plotly_chart(bfig, width="stretch")
            st.caption("Each bar = how much that driver's long-term change has added to (+) or removed from (−) the Dunkelflaute trend, "
                       "found by re-running history with the driver's trend taken out. Line = 95% bootstrap range; blue = significant "
                       "(Holm-corrected). Ranges include uncertainty in the driver's own trend. Drivers can cancel each other out, so we show amounts, not percentages.")
        show = drv_tab[["label", "unit", "trend_decade", "trend_p", "sens_slope", "sens_p", "implied_contribution_decade"]].copy()
        show.columns = ["Driver", "Unit", "Trend /decade", "Trend p", f"Link to {metric}", "Link p", "Trend × link"]
        st.dataframe(show.style.format({"Trend /decade": "{:+.3f}", "Trend p": "{:.3f}", f"Link to {metric}": "{:+.2f}",
                                        "Link p": "{:.3f}", "Trend × link": "{:+.2f}"}), hide_index=True, width="stretch")
        st.caption("A driver explains the trend only if it is changing significantly **and** linked to Dunkelflaute "
                   "(year-to-year link measured on detrended series). ⚠️ Winter cloud cover jumps around 2004 with no trend before or after, "
                   "which points to a change in the satellite cloud record rather than the weather; treat its trend with caution.")

    # ---------------- events
    st.subheader("Event explorer")
    if len(ev):
        evs = ev.assign(season_year=events.season_year(pd.DatetimeIndex(ev["start"]), season).values).dropna(subset=["season_year"])
        efig = go.Figure(go.Scatter(x=evs["start"], y=evs["length"], mode="markers",
                                    marker=dict(size=6 + evs["severity"] / evs["severity"].max() * 18, color=BLUE, opacity=0.6),
                                    text=[f"{s:%d %b %Y}: {n} days" for s, n in zip(evs["start"], evs["length"])], hoverinfo="text"))
        efig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Length (days)")
        st.plotly_chart(efig, width="stretch")
        choices = evs.sort_values("severity", ascending=False).head(25)
    if len(ev) and len(choices):
        pick = st.selectbox("Look inside one of the 25 most severe events",
                            choices.index, format_func=lambda i: f"{choices.loc[i, 'start']:%d %b %Y} — {choices.loc[i, 'length']} days")
        e = evs.loc[pick]
        win = slice(e["start"] - pd.Timedelta(days=10), e["end"] + pd.Timedelta(days=10))
        dd = regional_daily().loc[win]
        cfw = cf.loc[win]
        wfig = go.Figure()
        wfig.add_scatter(x=cfw.index, y=cfw.values, name="Combined output (CF)", line=dict(color="black", width=3))
        wfig.add_hline(y=thr_cf, line_dash="dot", annotation_text="low-output threshold")
        wfig.add_vrect(x0=e["start"], x1=e["end"] + pd.Timedelta(days=1), fillcolor=ORANGE, opacity=0.15, line_width=0)
        wfig.add_scatter(x=dd.index, y=dd["wind_hub"], name="Wind at 100 m (m/s)", yaxis="y2", line=dict(color=BLUE))
        wfig.add_scatter(x=dd.index, y=dd["ghi"], name="Sunlight (kWh/m²/day)", yaxis="y2", line=dict(color=ORANGE))
        wfig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2),
                           yaxis=dict(title="Capacity factor"), yaxis2=dict(title="Weather", overlaying="y", side="right"))
        st.plotly_chart(wfig, width="stretch")

    # ---------------- findings
    st.subheader("Findings summary")
    verdict = lambda tt: "a statistically significant" if tt["significant"] else "no statistically significant"
    st.info(
        f"Over {config.REGION_NAME}, {'winter' if season == 'winter' else 'annual'} Dunkelflaute shows {verdict(t_count)} change in **frequency** "
        f"({fmt_s(t_count['slope_decade'])} events per decade, {fmt_p(t_count['p_mk_mod'])}) and {verdict(t_len)} change in **typical length** "
        f"({fmt_s(t_len['slope_decade'])} days per decade, {fmt_p(t_len['p_mk_mod'])}). "
        f"For {METRIC_LABELS[metric].lower()}, the recent period averages {pc['recent_mean']:.2f} versus {pc['baseline_mean']:.2f} in {base[0]}–{base[1]}. "
        f"{up} of {len(cells)} grid cells show a significant rise and {down} a significant fall."
    )

with tab_walk:
    st.header("Become a trend detective in five steps")
    st.markdown("Follow along with the default settings (press **Reset to default settings** in the sidebar first).")
    st.markdown("""
1. **Ask the question.** Dunkelflaute is German for 'dark doldrums': days when wind turbines *and* solar panels produce very little.
   We ask: *are these spells becoming more common or longer?*
2. **Build the time series.** For every day since 1984 we turn NASA weather data into the power a fixed, unchanging set of turbines and
   panels would produce. Days in the lowest 10% count as 'low'; two or more low days in a row make an event. Look at the bars on the Dashboard.
3. **Test the trend.** A line through noisy data can slope by chance. The **Mann-Kendall test** asks whether the ups outnumber the downs
   more than chance allows. If *p* is below 0.05, we call the trend **significant**. Check the verdict cards.
4. **Find where.** The map runs the same test in every grid cell. Some regions can rise while others fall — that is exactly what the challenge asks us to look for.
5. **Ask why.** Switch **Wind speed** off in the sidebar. The orange line shows what would have happened if wind had no long-term trend.
   The gap between the lines is wind's share. Then try **Solar irradiance**.
""")
    st.success("Detective tip: try a different threshold or turbine. A real trend should survive small changes to the definition.")

with tab_defs:
    st.header("Plain-language definitions")
    st.markdown("""
| Term | What it means |
|---|---|
| **Dunkelflaute** | A spell of at least 2 days when combined wind and solar output stays very low. |
| **Capacity factor (CF)** | Power produced as a share of the maximum possible. 0.30 means 30% of full power. |
| **Fixed fleet** | We use the same turbine and panel for every year, so changes come from the weather, not from new technology. |
| **Baseline** | 1984–2013, the 30-year reference period used to set the 'low output' threshold. |
| **Trend** | A steady rise or fall over the years, measured per decade. |
| **Mann-Kendall test** | Checks whether values keep going up (or down) more often than chance would produce. |
| **Sen's slope** | A robust estimate of how fast something changes: the middle of all the year-to-year slopes. |
| **p-value** | The chance of seeing a trend this strong if there were really no trend. Below 0.05 = 'significant'. |
| **False-discovery-rate (FDR)** | A correction so that testing many map cells at once doesn't flag some by luck. |
| **Bootstrap range** | We reshuffle the years 1,000 times to see how much a result could vary; the middle 95% is the range. |
| **NAO** | North Atlantic Oscillation, a see-saw in air pressure that steers Europe's winter winds. |
| **Wind at 100 m** | Turbine hub height. NASA gives wind at 50 m; we scale it up with a standard formula. |
""")

with tab_method:
    st.header("Method and data")
    st.markdown(f"""
- **Data:** NASA POWER daily point data, 1984–2025, on a 1° grid ({len(load_panel().points)} points) over {config.REGION_NAME}.
  Wind and temperature come from NASA's **MERRA-2** reanalysis; sunlight and cloud from NASA **CERES SYN1deg** and **GEWEX SRB**.
- **Wind power:** 50 m wind scaled to hub height (power law, α = 1/7), passed through a generic turbine power curve, averaged over an
  assumed hour-to-hour spread within each day (sd = {config.INTRADAY_CV:.0%} of the daily mean).
- **Solar power:** daily irradiance ÷ 24 h at 1 kW/m² rating × performance ratio {config.PV_PERFORMANCE_RATIO}.
- **Events:** regional (area-mean) combined CF below the {config.DEFAULT.threshold_pct:g}th percentile of baseline days for ≥ {config.DEFAULT.min_days} days.
- **Statistics:** Mann-Kendall with Hamed-Rao autocorrelation correction; Sen's slope with 95% CI; Mann-Whitney recent vs baseline;
  Poisson regression on counts; Pettitt change-point; Benjamini-Hochberg FDR across cells.
- **Attribution:** counterfactual runs with each direct driver's long-term trend removed (same threshold); moving-block bootstrap
  (5-year blocks, 1,000 resamples, paired, re-estimating the driver's trend each time) for 95% ranges; Holm correction across drivers. Indirect drivers: trend × detrended sensitivity.
- **Limitations:** daily data smooths hour-to-hour swings; a single reanalysis; a fixed hypothetical fleet rather than the real one.
""")
    st.markdown("Code: [github.com/asakti47/dunkelflaute-explorer](https://github.com/asakti47/dunkelflaute-explorer)")
