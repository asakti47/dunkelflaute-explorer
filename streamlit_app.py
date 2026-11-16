"""Dunkelflaute Explorer - NASA Space Apps 2026, Be An Earth System Trend Detective!

Run locally with:  streamlit run streamlit_app.py

AI disclosure: this file was generated with the assistance of Claude (Anthropic), a generative AI
model, as part of the Dunkelflaute Explorer for NASA Space Apps 2026. The team directed the work and
reviewed and tested the code.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dfx import analysis, config, events, stats
from dfx.panel import DRIVER_LABELS, Panel, detrend_factor

__ai_generated__ = True
__ai_tool__ = "Claude (Anthropic)"
__ai_disclosure__ = "Code generated with AI assistance; directed, reviewed and tested by the team."

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


METRIC_UNITS = {"count": "events", "mean_len": "days", "max_len": "days", "total_days": "days", "severity": "CF-days"}
RISE, FALL = "#c0392b", "#2a6fdb"
CITIES = [  # reference places for describing grid locations
    ("Kiel", 54.32, 10.14), ("Flensburg", 54.79, 9.44), ("Rostock", 54.09, 12.10), ("Hamburg", 53.55, 10.00),
    ("Bremen", 53.08, 8.80), ("Groningen", 53.22, 6.57), ("Szczecin", 53.43, 14.55), ("Schwerin", 53.63, 11.41),
    ("Hanover", 52.37, 9.73), ("Berlin", 52.52, 13.40), ("Magdeburg", 52.13, 11.63), ("Münster", 51.96, 7.63),
    ("Osnabrück", 52.28, 8.05), ("Dortmund", 51.51, 7.47), ("Düsseldorf", 51.23, 6.78), ("Kassel", 51.31, 9.48),
    ("Leipzig", 51.34, 12.37), ("Dresden", 51.05, 13.74), ("Erfurt", 50.98, 11.03), ("Cottbus", 51.76, 14.33),
    ("Cologne", 50.94, 6.96), ("Aachen", 50.78, 6.08), ("Koblenz", 50.36, 7.59), ("Frankfurt", 50.11, 8.68),
    ("Würzburg", 49.79, 9.95), ("Chemnitz", 50.83, 12.92), ("Prague", 50.08, 14.44), ("Liège", 50.63, 5.57),
    ("Luxembourg", 49.61, 6.13), ("Saarbrücken", 49.24, 6.99), ("Mannheim", 49.49, 8.47), ("Nuremberg", 49.45, 11.08),
    ("Regensburg", 49.01, 12.10), ("Plzeň", 49.74, 13.38), ("Strasbourg", 48.57, 7.75), ("Stuttgart", 48.78, 9.18),
    ("Augsburg", 48.37, 10.90), ("Munich", 48.14, 11.58), ("Passau", 48.57, 13.43), ("Linz", 48.31, 14.29),
    ("Freiburg", 47.99, 7.85), ("Basel", 47.56, 7.59), ("Zurich", 47.38, 8.54), ("Kempten", 47.73, 10.31),
    ("Innsbruck", 47.27, 11.40), ("Salzburg", 47.81, 13.06),
]


def place_name(lat: float, lon: float) -> str:
    """'near Hanover' when within 40 km of a reference place, else '75 km from Bremen'."""
    best = None
    for name, la, lo in CITIES:
        dy = (lat - la) * 111.0
        dx = (lon - lo) * 111.0 * np.cos(np.radians((lat + la) / 2))
        km = float(np.hypot(dx, dy))
        if best is None or km < best[1]:
            best = (name, km)
    return f"near {best[0]}" if best[1] <= 40 else f"{round(best[1], -1):.0f} km from {best[0]}"


SRC = {
    "power": "https://power.larc.nasa.gov/docs/methodology/data/sources/",
    "merra2": "https://doi.org/10.5067/VJAFPLI1CSIV",
    "srb": "https://doi.org/10.5067/GEWEXSRB/Rel4-IP_Shortwave_daily_utc_1",
    "ceres": "https://ceres.larc.nasa.gov/data/#syn1deg-level-3",
    "nao": "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii",
}


def _a(text: str, key: str) -> str:
    return f'<a href="{SRC[key]}" target="_blank">{text}</a>'


DRIVER_NOTES = {
    "wind_hub": ("Average daily wind speed, scaled from 50 m to turbine height (100 m).",
                 f"{_a('NASA POWER', 'power')} (WS50M), from the {_a('MERRA-2', 'merra2')} reanalysis, 1984–2025."),
    "ghi": ("Total sunlight reaching the ground per day.",
            f"{_a('NASA POWER', 'power')} (ALLSKY_SFC_SW_DWN), from the {_a('GEWEX SRB', 'srb')} satellite record to 2000 "
            f"and {_a('CERES SYN1deg', 'ceres')} from 2001."),
    "cloud": ("Share of the sky covered by cloud.",
              f"{_a('NASA POWER', 'power')} (CLOUD_AMT), from {_a('GEWEX SRB', 'srb')} to 2000 and "
              f"{_a('CERES SYN1deg', 'ceres')} from 2001."),
    "high_pressure_days": ("Number of days per season when regional average surface pressure is more than one standard deviation "
                           "(8.2 hPa) above its normal for that date. Normal = the 1984–2013 average for that day of the year, "
                           "smoothed over 31 days. The standard deviation is of all daily departures from normal in 1984–2013. "
                           "About 14% of days qualify.",
                           f"{_a('NASA POWER', 'power')} surface pressure (PS), from {_a('MERRA-2', 'merra2')}."),
    "t2m": ("Average air temperature 2 m above the ground.",
            f"{_a('NASA POWER', 'power')} (T2M), from {_a('MERRA-2', 'merra2')}."),
    "nao": ("North Atlantic Oscillation: the standardised pressure difference between Iceland and the Azores, "
            "which steers Europe's winter winds.",
            f"{_a('NOAA Climate Prediction Center', 'nao')}, monthly index."),
}


def info(text: str, right: bool = False) -> str:
    """Small circled 'i' that shows a note on hover."""
    side = " dfx-itip-r" if right else ""
    return f'<span class="dfx-info">i<span class="dfx-itip{side}"><span class="dfx-itip-box">{text}</span></span></span>'


def season_tag(season: str) -> str:
    text = "winter" if season == "winter" else "year"
    return f'<span class="dfx-season">{text}</span>'


def sig_tag(t: dict) -> str:
    if not t["significant"]:
        return '<span class="dfx-tag dfx-ns">not significant</span>'
    cls = "dfx-up" if t["slope_decade"] > 0 or t.get("direction") == "rising" else "dfx-down"
    return f'<span class="dfx-tag {cls}">significant</span>'


def card(title: str, value: str, units: str = "", context: str = "", tag: str = "", hover: str | None = None,
         desc: str = "") -> str:
    """One headline card: six rows (title, description, value, units, context, tag) that line up across all cards."""
    tip = f'<div class="dfx-tip">{hover}</div>' if hover else ""
    cls = "dfx-card dfx-hover" if hover else "dfx-card"
    return (f'<div class="{cls}"><div class="dfx-title">{title}</div><div class="dfx-desc">{desc}</div>'
            f'<div class="dfx-value">{value}</div>'
            f'<div class="dfx-units">{units}</div><div class="dfx-ctx">{context}</div><div class="dfx-sub">{tag}</div>{tip}</div>')


CARD_CSS = f"""
<style>
.dfx-cards {{display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); column-gap: 1.5rem; row-gap: 0.75rem;
  margin: 0.3rem 0 1rem 0;}}
@media (max-width: 1100px) {{ .dfx-cards {{grid-template-columns: repeat(2, minmax(0, 1fr));}} }}
.dfx-card {{position: relative; display: grid; grid-row: span 6; grid-template-rows: subgrid; row-gap: 0; align-content: start;}}
.dfx-title {{font-size: 0.875rem; line-height: 1.35; font-weight: 700; align-self: start;}}
.dfx-desc {{font-size: 0.875rem; line-height: 1.35; opacity: 0.85; padding: 0.1rem 0 0.3rem 0; align-self: start;}}
.dfx-value {{font-size: clamp(1.25rem, 1.8vw, 1.7rem); line-height: 1.2; font-weight: 400;}}
.dfx-units {{font-size: 0.9rem; line-height: 1.3; opacity: 0.75; padding-top: 0.1rem;}}
.dfx-ctx {{font-size: 0.8rem; line-height: 1.35; opacity: 0.65; padding-top: 0.2rem;}}
.dfx-sub {{font-size: 0.82rem; line-height: 1.5; padding-top: 0.35rem;}}
.dfx-hover {{cursor: help;}}
.dfx-nw {{white-space: nowrap;}}
.dfx-zero {{opacity: 0.55; font-weight: 600;}}
.dfx-tag {{display: inline-block; padding: 0.05rem 0.55rem; border-radius: 999px; font-weight: 600; font-size: 0.78rem;}}
.dfx-ns {{background: rgba(138,138,138,0.18); color: inherit;}}
.dfx-up {{background: {RISE}; color: #fff;}}
.dfx-down {{background: {FALL}; color: #fff;}}
.dfx-season {{display: inline-block; padding: 0 0.5rem; border-radius: 999px; font-weight: 600;
  background: rgba(124,77,255,0.13); color: #6a3fe0; border: 1px solid rgba(124,77,255,0.45); white-space: nowrap;}}
.dfx-rise {{color: {RISE}; font-weight: 600;}}
.dfx-fall {{color: {FALL}; font-weight: 600;}}
.dfx-tip {{display: none; position: absolute; top: 100%; left: 0; z-index: 1000; width: max-content; max-width: 360px;
  background: #ffffff; color: #262730; border: 1px solid rgba(49,51,63,0.2); border-radius: 0.5rem;
  box-shadow: 0 6px 18px rgba(0,0,0,0.15); padding: 0.7rem 0.85rem; font-size: 0.82rem; line-height: 1.45;}}
.dfx-hover:hover .dfx-tip {{display: block;}}
.dfx-key {{display: flex; flex-wrap: wrap; gap: 0.6rem 1.6rem; align-items: flex-start; font-size: 0.82rem;
  margin: 0.2rem 0 0.4rem 0;}}
.dfx-key-item {{display: flex; align-items: center; gap: 0.45rem;}}
.dfx-key-list {{display: flex; flex-direction: column; gap: 0.35rem; padding-top: 0.05rem;}}
.dfx-key-icon {{display: inline-flex; width: 1.1rem; justify-content: center;}}
.dfx-key-scale {{flex-direction: column; align-items: stretch; gap: 0.15rem; min-width: 220px; flex: 1 1 220px; max-width: 320px;}}
.dfx-key-bar {{height: 12px; border-radius: 3px; border: 1px solid rgba(49,51,63,0.15);}}
.dfx-key-ticks {{display: flex; justify-content: space-between; line-height: 1.25; font-size: 0.76rem;}}
.dfx-key-ticks span:nth-child(2) {{text-align: center;}}
.dfx-key-ticks span:last-child {{text-align: right;}}
.dfx-key-unit {{font-size: 0.74rem; opacity: 0.7; text-align: center;}}
.dfx-key-sym {{font-size: 1.15rem; line-height: 1;}}
.dfx-key-dot {{display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #111;}}
.dfx-info {{position: relative; display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px;
  margin-left: 4px; border: 1px solid currentColor; border-radius: 50%; font-size: 9.5px; font-weight: 700; font-style: normal;
  line-height: 1; opacity: 0.55; cursor: help; vertical-align: 1px;}}
.dfx-info:hover {{opacity: 1;}}
.dfx-itip {{display: none; position: absolute; top: 100%; left: -8px; z-index: 1000; width: 280px; padding: 8px 0 0 0;
  font-size: 0.78rem; font-weight: 400; line-height: 1.45; text-align: left; white-space: normal; opacity: 1;}}
.dfx-itip > span, .dfx-itip-in {{display: block;}}
.dfx-itip::before {{content: ""; display: none;}}
.dfx-info:hover .dfx-itip {{display: block;}}
.dfx-itip-r {{left: auto; right: -8px;}}
.dfx-itip-box {{display: block; background: #ffffff; color: #262730; border: 1px solid rgba(49,51,63,0.2); border-radius: 0.5rem;
  box-shadow: 0 6px 18px rgba(0,0,0,0.15); padding: 0.6rem 0.75rem;}}
.dfx-itip-box b {{font-weight: 600;}}
.dfx-itip-box a {{color: #2a6fdb;}}
.dfx-dt {{width: 100%; border-collapse: collapse; font-size: 0.82rem; margin: 0.4rem 0 0.6rem 0;}}
.dfx-dt th {{text-align: right; font-weight: 600; padding: 0.4rem 0.45rem; border-bottom: 1px solid rgba(49,51,63,0.2);
  vertical-align: bottom; line-height: 1.3;}}
.dfx-dt td {{text-align: right; padding: 0.4rem 0.45rem; border-bottom: 1px solid rgba(49,51,63,0.08); font-variant-numeric: tabular-nums;}}
.dfx-dt th:first-child, .dfx-dt td:first-child, .dfx-dt th:nth-child(2), .dfx-dt td:nth-child(2) {{text-align: left;}}
.dfx-dt td:first-child {{white-space: nowrap;}}
.dfx-steps {{font-size: 0.85rem; line-height: 1.5; opacity: 0.85; margin: 0.2rem 0 0.8rem 0;}}
.dfx-steps ol {{margin: 0.25rem 0 0.35rem 1.2rem; padding: 0;}}
.dfx-steps li {{margin: 0.1rem 0;}}
.dfx-tip ul {{margin: 0.35rem 0 0.4rem 1.1rem; padding: 0;}}
.dfx-tip li {{margin: 0.1rem 0;}}
.dfx-tip .dfx-foot {{opacity: 0.7; font-size: 0.76rem; margin-top: 0.3rem;}}
</style>
"""


# ------------------------------------------------------------------ sidebar controls
st.sidebar.title("Controls")
if st.sidebar.button("Reset to default settings"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
season = st.sidebar.radio("Season", ["winter", "year"], format_func=lambda s: "Winter (Nov–Feb)" if s == "winter" else "Full year",
                          key="season", help="Dunkelflaute is mostly a winter problem: short days, low sun, calm high-pressure spells.")
st.sidebar.markdown(f'<div style="font-size:0.85rem;margin:-0.4rem 0 0.4rem 0">Shown on the cards as {season_tag(season)}</div>',
                    unsafe_allow_html=True)
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
st.html(CARD_CSS)  # page-wide styles; placed in the main area so they load even when the sidebar is collapsed
st.title("Dunkelflaute Explorer")
st.markdown(f"**Is the 'dark doldrums' — long spells with little wind *and* little sun — getting more frequent or longer over {config.REGION_NAME}, and why?**  \n"
            f"**Baseline:** {config.BASELINE[0]}–{config.BASELINE[1]}, which sets the low-output cut-off and the 'before' period in comparisons  \n"
            "Methodology, data sources and usage, assumptions and limitations, and the full code are on "
            "[GitHub](https://github.com/asakti47/dunkelflaute-explorer#readme).")

st.divider()
tab_dash = st.container()

with tab_dash:
    # ---------------- verdict cards
    tag = season_tag(season)
    per = "winter" if season == "winter" else "year"
    span = f"<span class='dfx-nw'>{int(m.index.min())}–{int(m.index.max())}</span>"
    cards = [
        card("Change in Dunkelflaute frequency", fmt_s(t_count["slope_decade"]),
             f"events per {per}, per decade", f"Average: {m['count'].mean():.1f} events per {per}, {span}",
             f"{sig_tag(t_count)} <span class='dfx-nw'>· {fmt_p(t_count['p_mk_mod'])}</span>", desc=f"events per {tag}"),
        card("Change in Dunkelflaute event length", fmt_s(t_len["slope_decade"]),
             "days per event, per decade", f"Average: {m['mean_len'].mean():.1f} days per event, {span}",
             f"{sig_tag(t_len)} <span class='dfx-nw'>· {fmt_p(t_len['p_mk_mod'])}</span>",
             desc=f"average days per event, each {tag}"),
    ]
    cells = run_cells(key(d), metric)
    sig_cells = cells[cells["significant_fdr"]].sort_values("slope_decade")
    up = int((sig_cells["slope_decade"] > 0).sum())
    down = int((sig_cells["slope_decade"] < 0).sum())
    measure = METRIC_LABELS[metric].split(" (")[0]
    unit = METRIC_UNITS[metric]
    season_word = "winter" if season == "winter" else "full year"
    if len(sig_cells):
        items = "".join(
            f"<li><b>{place_name(r.lat, r.lon)}</b> ({r.lat:.1f}°N, {r.lon:.1f}°E): "
            f'<span class="{"dfx-rise" if r.slope_decade > 0 else "dfx-fall"}">{fmt_s(r.slope_decade, 2)} {unit} per decade</span></li>'
            for r in sig_cells.itertuples())
        body = f"<ul>{items}</ul>"
    else:
        body = "<div style='margin:0.35rem 0'>No location has a significant trend.</div>"
    hover = (f"<b>Significant trends in {measure[0].lower() + measure[1:]}, {season_word}</b>{body}"
             "<div class='dfx-foot'>FDR = false discovery rate: a correction for testing 80 locations at once.</div>")
    cards.append(card("Locations with a significant trend",
                      f'<span class="dfx-nw {"dfx-rise" if up else "dfx-zero"}">{up} rising</span> · '
                      f'<span class="dfx-nw {"dfx-fall" if down else "dfx-zero"}">{down} falling</span>',
                      f"of {len(cells)} grid location cells (after FDR)", "Hover for locations", hover=hover))
    drv_tab, att, cfs = run_drivers(key(d), metric)
    sig = att[att["significant_holm"]] if len(att) else att
    if len(sig):
        short = {"wind_hub": "Wind", "ghi": "Sun"}
        parts = [f'<span class="dfx-nw">{short[k]} {fmt_s(r.reduction_decade, 1)}</span>' for k, r in sig.iterrows()]
        cards.append(card("Driver effects (significant)", " · ".join(parts),
                          f"{measure[0].lower() + measure[1:]} per decade"))
    else:
        cards.append(card("Driver effects", "None", "wind & sun trends: no significant effect"))
    st.markdown(f'<div class="dfx-cards">{"".join(cards)}</div>', unsafe_allow_html=True)

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
    xt = "Winter (Nov–Feb, labelled by its January year)" if season == "winter" else "Year"
    fig.update_layout(height=410, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.28),
                      yaxis_title=METRIC_LABELS[metric], xaxis_title=xt)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Recent ({config.RECENT[0]}–{config.RECENT[1]}) average {pc['recent_mean']:.2f} vs baseline {pc['baseline_mean']:.2f} "
               f"(ratio {pc['ratio']:.2f}, Mann-Whitney {fmt_p(pc['p_mannwhitney'])}). "
               f"Sen's slope 95% range: {fmt_s(t.get('ci_low', 0))} to {fmt_s(t.get('ci_high', 0))} per decade.")

    # ---------------- map + drivers
    left, right = st.columns(2)
    with left:
        st.subheader("Where is it changing?")
        lim = float(np.nanmax(np.abs(cells["slope_decade"]))) or 1.0
        mname = measure[0].lower() + measure[1:]
        st.markdown(f"Change in {mname} per decade, {season_word}, at each of {len(cells)} grid location cells (1° squares).")
        stops = ["#053061", "#2166ac", "#4393c3", "#92c5de", "#d1e5f0", "#f7f7f7", "#fddbc7", "#f4a582", "#d6604d", "#b2182b", "#67001f"]
        st.markdown(f"""
<div class="dfx-key">
  <div class="dfx-key-item dfx-key-scale">
    <div class="dfx-key-bar" style="background: linear-gradient(to right, {', '.join(stops)});"></div>
    <div class="dfx-key-ticks"><span>{-lim:.2f}<br><b>Fewer</b></span><span>0<br><b>No change</b></span><span>+{lim:.2f}<br><b>More</b></span></div>
    <div class="dfx-key-unit">{unit} per decade</div>
  </div>
  <div class="dfx-key-list">
    <div class="dfx-key-item"><span class="dfx-key-icon"><span class="dfx-key-sym">★</span></span>Significant trend (after FDR)</div>
    <div class="dfx-key-item"><span class="dfx-key-icon"><span class="dfx-key-dot"></span></span>City, for orientation</div>
  </div>
</div>""", unsafe_allow_html=True)
        grid = cells.pivot(index="lat", columns="lon", values="slope_decade")
        pv = cells.pivot(index="lat", columns="lon", values="p")
        sg = cells.pivot(index="lat", columns="lon", values="significant_fdr")
        hover_txt = [[(f"<b>{place_name(la, lo)}</b><br>{la:.1f}°N, {lo:.1f}°E<br>{grid.loc[la, lo]:+.2f} {unit} per decade"
                       f"<br>{fmt_p(pv.loc[la, lo])}<br>{'Significant (after FDR)' if sg.loc[la, lo] else 'Not significant'}")
                      for lo in grid.columns] for la in grid.index]
        mfig = go.Figure(go.Heatmap(z=grid.values, x=grid.columns, y=grid.index, colorscale="RdBu_r", zmin=-lim, zmax=lim,
                                    showscale=False, text=hover_txt, xgap=2, ygap=2,
                                    hovertemplate="%{text}<extra></extra>"))
        sig = cells[cells["significant_fdr"]]
        mfig.add_scatter(x=sig["lon"], y=sig["lat"], mode="markers", marker=dict(symbol="star", size=16, color="black"),
                         name="significant", hoverinfo="skip")
        cities = (("Hamburg", 53.55, 10.0), ("Berlin", 52.52, 13.4), ("Cologne", 50.94, 6.96), ("Munich", 48.14, 11.58))
        mfig.add_scatter(x=[c[2] for c in cities], y=[c[1] for c in cities], text=[c[0] for c in cities],
                         mode="markers+text", textposition="middle right", hoverinfo="skip",
                         marker=dict(size=6, color="#111"), textfont=dict(size=11, color="#111"))
        mfig.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                           xaxis=dict(dtick=1, ticksuffix="°E", showgrid=False, title="Longitude"),
                           yaxis=dict(dtick=1, ticksuffix="°N", showgrid=False, scaleanchor="x", scaleratio=1.5, title="Latitude"),
                           hoverlabel=dict(bgcolor="white", font_size=12))
        st.plotly_chart(mfig, width="stretch")
    with right:
        st.subheader("Why is it changing?")
        mname_w = measure[0].lower() + measure[1:]
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
            st.markdown(f"""<div class="dfx-steps">Each bar shows how much a driver's long-term trend has <b>added to</b> (bar to the right)
or <b>removed from</b> (bar to the left) {mname_w}, in {unit} per decade.<br><b>How it's calculated:</b>
<ol>
<li>Fit a straight-line trend through the driver's yearly averages, 1984–2025.</li>
<li>Rescale every day of each year by one factor, so those yearly averages sit on a flat line. Day-to-day and year-to-year weather is unchanged; only the trend is removed.</li>
<li>Re-run the model on the rescaled data, then compare its Dunkelflaute trend with the actual trend. The difference is the bar.</li>
<li>The line through each bar is the 95% range from 1,000 bootstrap re-runs, which resample the years in 5-year blocks and re-fit the driver's trend each time.</li>
</ol>Blue bars are statistically significant; grey bars are not.</div>""", unsafe_allow_html=True)
        keys = drv_tab["driver"] if "driver" in drv_tab.columns else drv_tab.index
        link_name = f"Link to {mname_w}" if mname_w.startswith(("total", "dunkel")) else f"Link to Dunkelflaute {mname_w}"
        heads = [
            ("Driver", None), ("Unit", None),
            ("Trend /decade", "How much the driver itself changed per decade, in its own units (Sen's slope)."),
            ("Trend p", "The chance of a trend this strong if the driver hadn't really changed. Below 0.05 = significant."),
            (link_name, f"In years when the driver was 1 unit higher than usual, how much {mname_w} rose (+) or fell (−), "
                        f"in {unit}. Long-term trends are removed from both first, so this measures year-to-year swings only."),
            ("Link p", "Whether that link could be chance. Below 0.05 = a real link."),
            ("Trend × link", f"Rough estimate of how much the driver's change accounts for in {mname_w}, in {unit} per decade: "
                             "trend × link."),
        ]
        th = "".join(f"<th>{h}{info(t, right=i >= 4) if t else ''}</th>" for i, (h, t) in enumerate(heads))
        rows = []
        for k, r in zip(keys, drv_tab.itertuples()):
            desc, src = DRIVER_NOTES.get(k, ("", ""))
            note = f"{desc}<br><br><b>Source:</b> {src}" if desc else ""
            rows.append(f"<tr><td>{r.label}{info(note) if note else ''}</td><td>{r.unit}</td>"
                        f"<td>{r.trend_decade:+.3f}</td><td>{r.trend_p:.3f}</td><td>{r.sens_slope:+.2f}</td>"
                        f"<td>{r.sens_p:.3f}</td><td>{r.implied_contribution_decade:+.2f}</td></tr>")
        st.markdown(f'<table class="dfx-dt"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table>',
                    unsafe_allow_html=True)

    # ---------------- events
    st.subheader("Event explorer")
    if len(ev):
        evs = ev.assign(season_year=events.season_year(pd.DatetimeIndex(ev["start"]), season).values).dropna(subset=["season_year"])
        efig = go.Figure(go.Scatter(x=evs["start"], y=evs["length"], mode="markers",
                                    marker=dict(size=6 + evs["severity"] / evs["severity"].max() * 18, color=BLUE, opacity=0.6),
                                    text=[f"{s:%d %b %Y}: {n} days" for s, n in zip(evs["start"], evs["length"])], hoverinfo="text"))
        efig.update_layout(height=290, margin=dict(l=10, r=10, t=10, b=10),
                           xaxis_title="Year (event start date)", yaxis_title="Dunkelflaute event length (days)")
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

st.caption("Built with AI assistance (Claude)")
