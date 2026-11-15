# UX review follow-up

This update applies the review to the existing NASA POWER fixed-fleet simulation.
It preserves the analysis definition and distinguishes this model from reported
electricity generation.

## Implemented

- Overview leads with the selected season's finding and time series; the trend
  estimate and 95% interval follow the chart. Events and Method & data are the
  other two tabs. Model settings and More analysis start collapsed.
- A top summary shows event frequency and length with corrected Mann–Kendall
  significance and p-values, FDR-significant grid-cell counts, and Holm-significant
  modeled driver effects. Counts and effects follow the selected measure; all
  headline tests use historical weather regardless of comparison toggles.
- Headline cards share label/value/detail rows so the main values align.
  Rising and falling counts have separate hover/focus tooltips listing the
  significant sample coordinates and signed trend values. Zero counts have an
  explicit empty message; counts use corrected significance, not raw p-values.
- Modeled-data provenance and the live percentile-to-capacity-factor rule appear
  above results and beside event inspection. Winter naming and full-run onset
  accounting are explicit.
- A wrapping selected-metric trend summary shows units, 95% slope interval,
  season count and an inconclusive verdict when the interval spans zero.
- Reset uses a callback. Checked weather switches now mean trend removal, with
  explicit scope limited to the long-term comparison.
- The Events tab opens event inspection. All eligible events are selectable,
  ranked by severity, with stable start-date selection and an explanation if
  changed settings remove the previous start date.
- Uniform event markers remove the unexplained size encoding. Grid-cell trends
  have a data table, units, significance labels and a rescaling disclosure.
- Event CF is formatted as percent with a labeled dashed cutoff; wind and
  irradiance have separate aligned rows. Event-day values are available in a
  table and CSV download.
- Data-load errors offer retry; empty events show recovery guidance. A spinner
  and selected-event summary identify the event being updated.
- Short explanations beside the chart and Method use simulation/sensitivity language and explain
  coverage limitations rather than implying audited observations.

## Validation and remaining work

`tests/test_dashboard.py` runs with the local environment's Python, or pytest.
It checks the real default dashboard, event selection across comparison changes,
threshold changes, reset synchronization, event-day cutoff membership, a
controlled data-read failure and retry, and an empty-event fixture.

The local Streamlit health endpoint responds successfully. Automated app checks
do not establish visual accessibility conformance. Browser inspection was
unavailable in this session because the browser access host was unavailable.
Light/dark contrast measurement, 320 px layout, 400% zoom, keyboard focus,
screen-reader announcements and delayed-update behavior still need live review.

Reported-generation studies, audited coverage, countries/common winters,
daily map replay, fixed CF breaks and validated event/seasonal-reference weather
scenarios require additional datasets and model validation. They remain outside
this simulation; no reported-generation result or causal attribution is claimed.
