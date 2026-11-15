"""Dunkelflaute Explorer - NASA Space Apps 2026, Be An Earth System Trend Detective!

Run locally with:  streamlit run streamlit_app.py
"""
from __future__ import annotations

from plotly.subplots import make_subplots

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dfx import analysis, config, events, stats
from dfx.panel import DRIVER_LABELS, Panel, detrend_factor
from dfx.headlines import headline_html

st.set_page_config(page_title="Dunkelflaute Explorer", layout="wide")

BLUE, ORANGE, GREY = "#2a6fdb", "#e8743b", "#8a8a8a"
METRIC_LABELS = events.METRICS | {"total_days": "Days in events that start this season"}


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
CONTROL_DEFAULTS = dict(season="winter", metric="total_days", thr=10, min_days=2,
                        mix=0.5, turbine="default", remove_wind=False, remove_ghi=False)


def reset_controls():
    st.session_state.update(CONTROL_DEFAULTS)
    st.session_state.pop("event_date", None)


for control, default in CONTROL_DEFAULTS.items():
    st.session_state.setdefault(control, default)

st.sidebar.title("Controls")
st.sidebar.button("Reset", on_click=reset_controls)
season = st.sidebar.radio("Season", ["winter", "year"], index=None, format_func=lambda s: "Winter (Nov–Feb)" if s == "winter" else "Full year",
                          key="season", help="Dunkelflaute is mostly a winter problem: short days, low sun, calm high-pressure spells.")
st.sidebar.caption(f"Period: 1984–2025 · Baseline: {config.BASELINE[0]}–{config.BASELINE[1]}")
metric = st.sidebar.selectbox("Measure", list(METRIC_LABELS), index=None, format_func=METRIC_LABELS.get, key="metric")
with st.sidebar.expander("Model settings", expanded=False):
    thr = st.slider("Low-output threshold (percentile of baseline days)", 5, 25, step=5, key="thr",
                            help="A day counts as 'low' if combined wind + solar output is below this percentile of all 1984–2013 days.")
    min_days = st.radio("Minimum event length", [1, 2, 3], index=None, horizontal=True, format_func=lambda n: f"{n} day{'s' if n > 1 else ''}", key="min_days")
    mix = st.slider("Wind share of the fleet", 0.0, 1.0, step=0.1, key="mix", help="Frozen mix of wind vs solar capacity.")
    turbine = st.selectbox("Turbine (frozen for all years)", list(config.TURBINES), index=None, format_func=lambda k: config.TURBINES[k].name, key="turbine")
    st.markdown("**Long-term weather sensitivity**")
    remove_wind = st.toggle("Remove long-term wind trend from comparison", key="remove_wind")
    remove_ghi = st.toggle("Remove long-term solar trend from comparison", key="remove_ghi")
    st.caption("Checked = remove that input's 1984–2025 trend while retaining daily variability. "
                       "Only the long-term comparison changes; event inspection uses historical weather.")

d = config.Definition(threshold_pct=float(thr), min_days=int(min_days), wind_share=float(mix), turbine=turbine, season=season)
try:
    load_panel()
except (OSError, ValueError, KeyError) as exc:
    st.error("Couldn't load weather data. Check the bundled data files, then retry.")
    st.caption(str(exc))
    if st.button("Retry weather data"):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()
    st.stop()

cf, ev, m, thr_cf, cf_m = run_regional(key(d), remove_wind, remove_ghi)
y = m[metric]
t = stats.trend(y)
pc = stats.period_compare(y)

# ------------------------------------------------------------------ header
st.title("Dunkelflaute Explorer")
st.write("Low wind and solar output in Germany, 1984–2025")
st.caption("Weather-based estimate for a hypothetical fixed fleet · NASA POWER · Germany and surroundings")

rule = (f"A drought is {min_days}+ consecutive days strictly below {thr_cf:.2%} modeled combined capacity factor. "
        f"This cutoff is the {thr:g}th percentile of 1984–2013 daily output for this fleet.")
unit = {"count": "events", "mean_len": "days", "max_len": "days", "total_days": "days",
        "severity": "CF shortfall × days"}[metric]
period = "winter" if season == "winter" else "annual"
measure = {"total_days": "low-output days", "count": "low-output event count",
           "mean_len": "typical low-output event length", "max_len": "longest low-output event",
           "severity": "low-output severity"}[metric]
interval_crosses_zero = t["ci_low"] <= 0 <= t["ci_high"]
finding = (f"No clear trend in {period} {measure}" if interval_crosses_zero
           else f"{'Rising' if t['slope_decade'] > 0 else 'Falling'} {period} {measure}")

tab_overview, tab_events, tab_method = st.tabs(["Overview", "Events", "Method & data"])

with tab_overview:
    frequency = stats.trend(m["count"])
    event_length = stats.trend(m["mean_len"])
    cells = run_cells(key(d), metric)
    drv_tab, att, cfs = run_drivers(key(d), metric)
    significant_effects = att[att["significant_holm"]] if len(att) else att
    names = {"wind_hub": "Wind", "ghi": "Solar"}
    effects = [f"{names.get(name, name)} {fmt_s(row.reduction_decade, 1)}"
               for name, row in significant_effects.iterrows()]
    st.html(headline_html(frequency, event_length, cells, effects, unit, METRIC_LABELS[metric].lower()))
    st.caption(f"Historical-weather simulation · {'Nov–Feb winters' if season == 'winter' else 'Calendar years'} · "
               "Frequency and length use the autocorrelation-corrected Mann–Kendall test (p < 0.05). "
               "Weather-trend removal switches affect the chart comparison, not these historical-weather tests.")

    st.subheader(finding)
    # ---------------- time series
    yrs = y.index.values
    fig = go.Figure()
    fig.add_bar(x=yrs, y=y.values, name="Events from historical weather", marker_color=BLUE, opacity=0.55)
    if t.get("n", 0) >= 8:
        line = t["intercept"] + t["slope_decade"] / 10 * yrs
        fig.add_scatter(x=yrs, y=line, name="Estimated trend",
                        line=dict(color=GREY, dash="dash"))
    roll = y.rolling(10, center=True, min_periods=5).mean()
    fig.add_scatter(x=yrs, y=roll.values, name="10-year average", line=dict(color=BLUE, width=3))
    if cf_m is not None:
        off = [n for n, removed in (("wind", remove_wind), ("solar", remove_ghi)) if removed]
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
                      yaxis_title=unit, xaxis_title=None)
    st.plotly_chart(fig, width="stretch")
    st.markdown(f"**Estimate: {fmt_s(t['slope_decade'])} {unit} per decade** · "
                f"95% interval: **{fmt_s(t['ci_low'])} to {fmt_s(t['ci_high'])} {unit} per decade** · "
                f"{t['n']} {'winters' if season == 'winter' else 'years'}")
    st.caption("An interval spanning zero leaves both a rise and a fall plausible; it does not establish no change.")
    st.caption(f"Recent ({config.RECENT[0]}–{config.RECENT[1]}) average: {pc['recent_mean']:.2f} "
               f"versus {pc['baseline_mean']:.2f} in {base[0]}–{base[1]}.")
    with st.expander("How to read the chart"):
        st.write("Bars show modeled low-output events for each season. The solid line is a 10-year average; "
                 "the dashed line estimates the long-term trend. Orange lines, when enabled in Model settings, "
                 "show the comparison with selected weather trends removed.")
        st.write(rule)
        st.caption("Capacity factor is output as a share of maximum possible output; 30% means 30% of full power. "
                   "Neither wind nor solar must individually cross a cutoff. "
                   "Winter means Nov–Feb, named by January year. Full event runs are assigned by start date, "
                   "so low-output day totals can include days beyond the season.")
        st.caption(f"Applied fleet: {mix:.0%} wind / {1-mix:.0%} solar · {config.TURBINES[turbine].name}. "
                   f"Autocorrelation-corrected Mann–Kendall {fmt_p(t['p_mk_mod'])}.")

    with st.expander("More analysis", expanded=False):
        # ---------------- map + drivers
        left, right = st.columns(2)
        with left:
            st.subheader(f"Local trend in modeled {METRIC_LABELS[metric].lower()}")
            st.caption(f"{unit} per decade · Grid-cell trends, not daily output or event selection.")
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
            st.caption("Each square is a 1° grid cell. Red = rising, blue = falling. ★ = significant after false-discovery-rate correction. The color range rescales with the selected settings.")
            with st.expander("View grid-cell trend data"):
                st.dataframe(cells[["lat", "lon", "slope_decade", "p", "significant_fdr"]], hide_index=True)
        with right:
            st.subheader("Sensitivity to long-term weather trends")
            if len(att):
                bfig = go.Figure()
                bfig.add_bar(y=[DRIVER_LABELS[k][0] for k in att.index], x=att["reduction_decade"], orientation="h",
                             marker_color=[BLUE if s else GREY for s in att["significant_holm"]],
                             error_x=dict(type="data", symmetric=False,
                                          array=att["reduction_high"] - att["reduction_decade"],
                                          arrayminus=att["reduction_decade"] - att["reduction_low"]))
                bfig.add_vline(x=0, line_color=GREY)
                st.caption(f"Modeled change in trend · {unit} per decade · Lines show 95% bootstrap intervals.")
                bfig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None)
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


with tab_events:
    # ---------------- events
    st.subheader("Event explorer", anchor="event-explorer")
    st.caption(rule)
    st.caption("Historical-weather simulation. Events are assigned by start date; full runs can extend beyond the season. "
               "Long-term weather comparison switches do not alter these events.")
    evs = ev.assign(season_year=events.season_year(pd.DatetimeIndex(ev["start"]), season).values).dropna(subset=["season_year"])
    evs = evs[evs["season_year"].isin(events.valid_years(season))]
    if len(evs):
        choices = evs.sort_values("severity", ascending=False).set_index("start", drop=False)
        dates = choices.index.strftime("%Y-%m-%d").tolist()
        previous = st.session_state.get("event_date")
        if previous not in dates:
            st.session_state.event_date = dates[0]
            if previous is not None:
                st.info(f"The previous event starting {previous} no longer qualifies under these settings. "
                        f"Showing {dates[0]}. Event boundaries can shift when the cutoff changes.")
        pick = st.selectbox("Inspect an event (most severe first)", dates, key="event_date",
                            format_func=lambda date: f"{date} — {int(choices.loc[pd.Timestamp(date), 'length'])} days")
        e = choices.loc[pd.Timestamp(pick)]
        st.caption(f"Updated event: {e['start']:%d %b %Y}–{e['end']:%d %b %Y} · "
                   f"{int(e['length'])} days · Lowest modeled CF {e['min_cf']:.2%} · Cutoff {thr_cf:.2%}")
        win = slice(e["start"] - pd.Timedelta(days=10), e["end"] + pd.Timedelta(days=10))
        dd = regional_daily().loc[win]
        cfw = cf.loc[win]
        with st.spinner(f"Updating event chart for {pick}…"):
            wfig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                                 subplot_titles=("Modeled capacity factor (%)", "Wind at 100 m (m/s)", "Sunlight (kWh/m²/day)"))
            wfig.add_scatter(x=cfw.index, y=cfw.values, name="Modeled output using historical weather",
                            line=dict(color=BLUE, width=3), row=1, col=1)
            wfig.add_hline(y=thr_cf, line_dash="dash", line_color=ORANGE,
                          annotation_text=f"Cutoff {thr_cf:.2%}", row=1, col=1)
            wfig.add_scatter(x=dd.index, y=dd["wind_hub"], name="Wind at 100 m", line=dict(color=BLUE), row=2, col=1)
            wfig.add_scatter(x=dd.index, y=dd["ghi"], name="Sunlight", line=dict(color=ORANGE), row=3, col=1)
            wfig.add_vrect(x0=e["start"], x1=e["end"] + pd.Timedelta(days=1), fillcolor=ORANGE,
                          opacity=0.15, line_width=0, row="all", col=1)
            wfig.update_yaxes(tickformat=".0%", row=1, col=1)
            wfig.update_xaxes(nticks=5)
            wfig.update_layout(height=650, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
            st.plotly_chart(wfig, width="stretch")
        with st.expander("Event history"):
            efig = go.Figure(go.Scatter(x=evs["start"], y=evs["length"], mode="markers",
                                        marker=dict(size=9, color=BLUE, opacity=0.6),
                                        text=[f"{s:%d %b %Y}: {n} days" for s, n in zip(evs["start"], evs["length"])], hoverinfo="text"))
            efig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Length (days)")
            st.plotly_chart(efig, width="stretch")
            st.caption("Markers have equal size. All eligible events are selectable below, ranked by severity (CF shortfall × days).")
        event_days = pd.DataFrame({"Date": cfw.index, "Modeled CF (%)": cfw.values * 100,
                                   "Cutoff (%)": thr_cf * 100, "Wind at 100 m (m/s)": dd["wind_hub"].values,
                                   "Sunlight (kWh/m²/day)": dd["ghi"].values,
                                   "Selected event": (cfw.index >= e["start"]) & (cfw.index <= e["end"])})
        with st.expander("View event-day data"):
            st.dataframe(event_days, hide_index=True, width="stretch")
            st.download_button("Download event-day data (CSV)", event_days.to_csv(index=False),
                               file_name=f"modeled-event-{pick}.csv", mime="text/csv")
        with st.expander("View all eligible events"):
            st.dataframe(evs, hide_index=True, width="stretch")
    else:
        st.info("No events match these settings. Try a higher threshold or shorter minimum duration.")

with tab_method:
    st.header("Method and data")
    st.markdown(f"""
- **Data:** NASA POWER daily point data, 1984–2025, on a 1° grid ({len(load_panel().points)} points) over {config.REGION_NAME}.
  Wind and temperature come from NASA's **MERRA-2** reanalysis; sunlight and cloud from NASA **CERES SYN1deg** and **GEWEX SRB**.
- **Wind power:** 50 m wind scaled to hub height (power law, α = 1/7), passed through a generic turbine power curve, averaged over an
  assumed hour-to-hour spread within each day (sd = {config.INTRADAY_CV:.0%} of the daily mean).
- **Solar power:** daily irradiance ÷ 24 h at 1 kW/m² rating × performance ratio {config.PV_PERFORMANCE_RATIO}.
- **Active event rule:** {rule}
- **Season accounting:** {"Nov–Feb, named by January year" if season == "winter" else "Full calendar years"}. Events are assigned by onset; day totals count the full run, including days outside the season. These totals are not in-winter burden.
- **Coverage:** regional CF averages available grid cells. Seasonal zero-event totals are filled with zero; this is not an audited coverage indicator. Missing observations are not proof of no drought. Reported-generation and country comparisons are unavailable in this weather-based simulation.
- **Statistics:** Mann-Kendall with Hamed-Rao autocorrelation correction; Sen's slope with 95% CI; Mann-Whitney recent vs baseline;
  Poisson regression on counts; Pettitt change-point; Benjamini-Hochberg FDR across cells.
- **Attribution:** counterfactual runs with each direct driver's long-term trend removed (same threshold); moving-block bootstrap
  (5-year blocks, 1,000 resamples, paired, re-estimating the driver's trend each time) for 95% ranges; Holm correction across drivers. Indirect drivers: trend × detrended sensitivity.
- **Limitations:** daily data smooths hour-to-hour swings; a single reanalysis; a fixed hypothetical fleet rather than the real one.
""")
    st.markdown("Code: [github.com/asakti47/dunkelflaute-explorer](https://github.com/asakti47/dunkelflaute-explorer)")
