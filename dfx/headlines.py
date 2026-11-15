"""Aligned headline cards with keyboard-accessible location tooltips."""
from html import escape


def headline_html(frequency, event_length, cells, effects, unit, measure):
    def number(value):
        return f"{0.0 if abs(value) < .005 else value:+.2f}"

    def test_caption(result, units):
        p = result["p_mk_mod"]
        p_text = "p < 0.001" if p < .001 else f"p = {p:.3f}"
        return f"{units} per decade · {'Significant' if result['significant'] else 'Not significant'} · {p_text}"

    def location_count(direction):
        sign = cells["slope_decade"] > 0 if direction == "rising" else cells["slope_decade"] < 0
        locations = cells[sign & cells["significant_fdr"]].sort_values(["lat", "lon"])
        rows = [f"{row.lat:.1f}°N, {row.lon:.1f}°E: {row.slope_decade:+.2f} {unit} per decade"
                for row in locations.itertuples()]
        content = ("<ul>" + "".join(f"<li>{escape(row)}</li>" for row in rows) + "</ul>"
                   if rows else f"No grid locations have a significant {direction} trend for these settings.")
        return (f'<span class="dfx-location"><button type="button" aria-describedby="dfx-{direction}-tooltip">'
                f'{len(locations)} {direction}</button><span class="dfx-tooltip" role="tooltip" '
                f'id="dfx-{direction}-tooltip"><strong>Significantly {direction} grid locations</strong>'
                f'{content}</span></span>')

    driver_value = (" · ".join(escape(value) for value in effects) if effects else "None detected")
    driver_caption = f"{unit} per decade · Holm-corrected · Selected measure: {measure}"
    if not effects:
        driver_caption = "No clear modeled driver effect for this setting. " + driver_caption
    cards = [
        ("Dunkelflaute frequency", number(frequency["slope_decade"]),
         test_caption(frequency, "events")),
        ("Dunkelflaute event length", number(event_length["slope_decade"]),
         test_caption(event_length, "days")),
        ("Locations with a significant trend", location_count("rising") + ' <span aria-hidden="true">·</span> ' + location_count("falling"),
         f"of {len(cells)} grid cells · FDR-corrected · Selected measure: {measure}"),
        ("Weather-driver effects (significant)", driver_value, driver_caption),
    ]
    style = """<style>
    .dfx-headlines {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:0 1.5rem; margin:1rem 0;}
    .dfx-card {display:grid; grid-template-rows:subgrid; grid-row:span 3; gap:.65rem; min-width:0;}
    .dfx-card-label {font-size:1rem; font-weight:600; line-height:1.45; margin:0;}
    .dfx-card-value {display:flex; flex-wrap:nowrap; align-items:baseline; gap:.25em;
      font-size:clamp(1rem,1.6vw,1.4rem); line-height:1.25; font-weight:600; margin:0; align-self:start; white-space:nowrap;}
    .dfx-card-caption {font-size:.875rem; line-height:1.6; opacity:.7; margin:0; overflow-wrap:anywhere;}
    .dfx-location {position:relative; display:inline-block; flex:0 0 auto; white-space:nowrap;}
    .dfx-location button {display:inline-block; white-space:nowrap; font:inherit; color:inherit; border:0; padding:0; background:transparent; cursor:help;
      text-decoration:underline dotted; text-underline-offset:.2em;}
    .dfx-location button:focus-visible {outline:2px solid currentColor; outline-offset:4px; border-radius:2px;}
    .dfx-tooltip {display:none; position:absolute; top:100%; left:0; z-index:1000; width:22rem; max-width:75vw;
      max-height:20rem; overflow-y:auto; padding:1rem; border:1px solid #737d8a; border-radius:.4rem;
      background:#20242a; color:#fff; box-shadow:0 4px 14px #0004; font-size:.875rem; font-weight:400; line-height:1.6; white-space:normal;}
    .dfx-tooltip ul {margin:.5rem 0 0; padding-left:1.2rem;}
    .dfx-location:hover .dfx-tooltip,.dfx-location:focus-within .dfx-tooltip {display:block;}
    @media(max-width:1000px) {.dfx-headlines {grid-template-columns:repeat(2,minmax(0,1fr)); row-gap:.65rem;}}
    @media(max-width:520px) {.dfx-headlines {grid-template-columns:minmax(0,1fr);} .dfx-card-value {font-size:1.4rem;}}
    </style>"""
    return style + '<section class="dfx-headlines" aria-label="Trend significance summary">' + "".join(
        f'<article class="dfx-card"><p class="dfx-card-label">{escape(label)}</p>'
        f'<div class="dfx-card-value">{value}</div><p class="dfx-card-caption">{escape(caption)}</p></article>'
        for label, value, caption in cards) + '</section>'
