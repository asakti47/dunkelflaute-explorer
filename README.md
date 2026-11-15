# Dunkelflaute Explorer

NASA Space Apps Challenge 2026 · *Be An Earth System Trend Detective!*

## Executive Summary

**Dunkelflaute** is German for "dark doldrums": days when there is very little wind *and* very little sun, so wind turbines and solar panels both produce almost nothing. Power grids that rely on renewables must cover these spells some other way.

The Dunkelflaute Explorer answers three questions for Germany and its surroundings, using NASA data from 1984 to 2025:

1. **Is it changing?** Are these spells becoming more frequent or longer?
2. **Where?** Is the change the same everywhere, or different from region to region?
3. **Why?** Which weather ingredients (wind, sunlight, and so on) are behind the change?

**What it found:**

- **No significant change overall.** Dunkelflaute has not become more frequent or longer since 1984. Winters averaged about 18 Dunkelflaute days in 1984–2013 and 16 in 2014–2025, a difference that could easily be chance.
- **Extremes still happen.** The worst spell in the 42-year record was 4–13 November 2024.
- **Two forces cancel out.** Skies have become sunnier (fewer Dunkelflaute days), while winds may have weakened slightly (more days). The two roughly offset each other, so the total barely moves.
- **Regions differ.** Western Germany leans towards fewer Dunkelflaute days, the east towards more, though most individual locations are not significant on their own.

## Quick start

**Code:** [github.com/asakti47/dunkelflaute-explorer](https://github.com/asakti47/dunkelflaute-explorer)

**Run the dashboard locally** (Python 3.11 or later):

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

On first run the app rebuilds the data files in `data/` from the stored parts; this takes a few seconds.

**Other commands:**

| Command | What it does |
| --- | --- |
| `python scripts/run_analysis.py` | Runs the full analysis at default settings and writes every result table to `results/` |
| `python scripts/fetch_data.py` | Re-downloads all input data from NASA POWER and NOAA (needs internet access) |
| `python -m pytest -q tests` | Runs the unit tests |

## Inputs: data

All weather inputs are **daily** values from the [NASA POWER](https://power.larc.nasa.gov) API (Renewable Energy community), **1 January 1984 to 31 December 2025** (15,341 days), at **80 grid points**.

**Grid:** latitudes 47.5° to 54.5°N and longitudes 6° to 15°E in 1° steps (8 × 10 points), covering Germany and parts of its neighbours. Each point takes the value of the NASA source grid cell it falls in.

**Links:** [POWER daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) · [POWER data sources](https://power.larc.nasa.gov/docs/methodology/data/sources/) · [Example request](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=WS50M,T2M,PS,ALLSKY_SFC_SW_DWN,CLOUD_AMT&community=RE&longitude=10&latitude=51.5&start=19840101&end=20251231&format=CSV): all five variables for the grid point at 51.5°N, 10°E, 1984–2025, as CSV. `scripts/fetch_data.py` requests the same data for every grid point.

| Variable | POWER code | Unit | What it is | Original source | Used for |
| --- | --- | --- | --- | --- | --- |
| Wind speed at 50 m | `WS50M` | m/s | Daily mean wind speed 50 m above ground. POWER calculates it from the MERRA-2 50 m wind components | MERRA-2 reanalysis, hourly single-level diagnostics ([M2T1NXSLV, doi:10.5067/VJAFPLI1CSIV](https://doi.org/10.5067/VJAFPLI1CSIV)), 1984–2025 | Wind power output; wind driver |
| Surface solar irradiance | `ALLSKY_SFC_SW_DWN` | kWh/m²/day | Total sunlight reaching the ground in a day, including cloud effects | 1984–2000: [GEWEX SRB Release 4-IP, daily shortwave](https://asdc.larc.nasa.gov/project/SRB/GEWEXSRB_Rel4-IP_Shortwave_daily_utc_1); 2001–2025: [CERES SYN1deg Edition 4.1, daily](https://ceres.larc.nasa.gov/data/#syn1deg-level-3) | Solar power output; sun driver |
| Air temperature at 2 m | `T2M` | °C | Daily mean temperature | MERRA-2 reanalysis, hourly single-level diagnostics ([M2T1NXSLV, doi:10.5067/VJAFPLI1CSIV](https://doi.org/10.5067/VJAFPLI1CSIV)), 1984–2025 | Temperature driver |
| Surface pressure | `PS` | kPa | Daily mean air pressure at ground level | MERRA-2 reanalysis, hourly single-level diagnostics ([M2T1NXSLV, doi:10.5067/VJAFPLI1CSIV](https://doi.org/10.5067/VJAFPLI1CSIV)), 1984–2025 | High-pressure days driver |
| Cloud amount | `CLOUD_AMT` | % | Share of the sky covered by cloud | 1984–2000: [GEWEX SRB Release 4-IP, daily shortwave](https://asdc.larc.nasa.gov/project/SRB/GEWEXSRB_Rel4-IP_Shortwave_daily_utc_1); 2001–2025: [CERES SYN1deg Edition 4.1, daily](https://ceres.larc.nasa.gov/data/#syn1deg-level-3) | Cloud driver |

The sources were confirmed from the `sources` field that POWER returns with each request: `MERRA2` for wind, temperature and pressure throughout; `SRB` for sunlight and cloud up to 31 December 2000 and `SYN1DEG` from 1 January 2001. NASA advises against trend analysis across that change (see *Assumptions and limitations*).

One further input, monthly:

| Variable | Unit | What it is | Source | Used for |
| --- | --- | --- | --- | --- |
| NAO index | dimensionless | North Atlantic Oscillation: a standardised measure of the air-pressure difference between Iceland and the Azores, which steers Europe's winter winds | [NOAA Climate Prediction Center](https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.nao.monthly.b5001.current.ascii) | NAO driver; NAO-controlled trend check |

**Storage:** `data/power_<variable>.csv.gz`, one file per variable. Rows are dates (`YYYYMMDD`), columns are grid points named `latitude_longitude` (for example `51.5_10.0`). Values are rounded to 1 decimal (wind, temperature), 2 decimals (sunlight, pressure) or whole numbers (cloud). Missing values would be stored as −999; there are none in 1984–2025. The NAO index is in `data/nao_monthly.csv` (columns `year`, `month`, `nao`).

## Inputs: user controls

Settings in the dashboard sidebar. Changing one recalculates the outputs listed in the last column.

| Control | Allowed values | Default | What it changes | Outputs affected |
| --- | --- | --- | --- | --- |
| **Season** | Winter (Nov–Feb), Full year | Winter | Which days count. Winter seasons are labelled by the January year (winter 2017 = Nov 2016 to Feb 2017), giving 41 winters (1985–2025); full year gives 42 calendar years (1984–2025). An event belongs to the season in which it starts | Everything |
| **Measure** | Event count, Mean event length, Longest event, Total Dunkelflaute days, Severity | Total Dunkelflaute days | Which seasonal measure is charted, mapped and attributed to drivers | Time series, caption, map, card 3, driver bars, card 4, driver table |
| **Low-output threshold** | 5, 10, 15, 20, 25 (percentile) | 10 | The cut-off below which a day counts as "low": this percentile of all daily output values in 1984–2013 | Everything |
| **Minimum event length** | 1, 2, 3 days | 2 | How many consecutive low days make one event | Everything |
| **Wind share of the fleet** | 0.0 to 1.0, steps of 0.1 | 0.5 | Share of capacity that is wind; the rest is solar | Everything |
| **Turbine** | Older 2000s, Reference 2020s, Modern low-wind | Reference 2020s | Which fixed power curve and hub height turn wind into output (see fixed assumptions) | Everything |
| **Wind speed** switch | On, Off | On | Off adds an orange line to the time series: the same history with wind's long-term trend removed | Time series only |
| **Solar irradiance** switch | On, Off | On | Off adds the same line with sunlight's long-term trend removed. With both off, both trends are removed | Time series only |
| **Reset to default settings** | button | – | Restores every default | Everything |
| **Event selector** (event explorer) | The 25 most severe events of the chosen season | Most severe | Which event is shown day by day | Event detail chart only |

The driver switches change only the time-series chart. The headline cards, map and driver bars always describe actual history; the driver bars already compare each driver's "trend removed" version.

## Inputs: fixed assumptions

Constants built into the model (`dfx/config.py`). They are the same for every year.

**Turbines.** Output is 0 below the cut-in speed, rises with the cube of wind speed up to the rated speed, stays at 100% up to the cut-out speed, then drops to 0.

| Turbine | Hub height | Cut-in | Rated (full power) | Cut-out |
| --- | --- | --- | --- | --- |
| Reference 2020s (default) | 100 m | 3.0 m/s | 12.0 m/s | 25 m/s |
| Older 2000s | 80 m | 4.0 m/s | 14.0 m/s | 25 m/s |
| Modern low-wind | 120 m | 3.0 m/s | 10.5 m/s | 25 m/s |

**Other constants:**

| Constant | Value | Purpose |
| --- | --- | --- |
| Wind height scaling exponent | 1/7 | Scales 50 m wind to hub height |
| Hour-to-hour wind spread | 25% of the daily mean (normal distribution) | Accounts for wind varying within a day, since only daily means are available |
| Solar rating basis | 1 kW/m² | A panel produces its rated power at this sunlight intensity |
| Solar performance ratio | 0.80 | System losses (inverters, temperature, dirt) |
| Regional weighting | Equal weight for all 80 points | Regional output and drivers are simple averages |
| Baseline period | 1984–2013 | Sets the low-output threshold and is the reference for comparisons |
| Recent period | 2014–2025 | Compared with the baseline |
| Significance level | 0.05 | A p-value below this counts as significant |
| Map correction | Benjamini-Hochberg false discovery rate, 5% | Corrects for testing 80 points at once |
| Bootstrap | 1,000 resamples, 5-year blocks, fixed random seed (42) | Ranges for driver effects |
| Driver correction | Holm method across the 2 drivers | Corrects for testing two drivers |
| Chart smoothing | 10-year centred average (at least 5 years) | The solid line on the time series |
| High-pressure day | Regional pressure more than 1 baseline standard deviation above its calendar-day normal (1984–2013 average, smoothed over 31 days) | Defines the high-pressure driver |

## How the model works

The model runs these steps in order. Steps 1–7 produce the headline numbers; steps 8–9 add the map and drivers.

**1. Wind output (each point, each day).** Scale the 50 m wind to hub height *h*, then average the turbine's power curve *P* over an assumed spread of hourly speeds around the daily mean:

```math
v_{hub} = v_{50}\left(\frac{h}{50}\right)^{1/7} \qquad CF_{wind} = \mathrm{E}\left[P\left(v_{hub}(1 + 0.25\,z)\right)\right],\; z \sim N(0,1)
```

**2. Solar output (each point, each day).** Daily sunlight *G* in kWh/m²/day:

```math
CF_{solar} = \frac{G}{24} \times 0.80
```

**3. Combined regional output (each day).** With wind share *s* (default 0.5), averaged over the 80 points:

```math
CF = \frac{1}{80}\sum_{points}\left[s\,CF_{wind} + (1-s)\,CF_{solar}\right]
```

**4. Threshold.** *T* = the chosen percentile (default 10th) of all daily *CF* values in 1984–2013. At default settings *T* = 0.086 (8.6% of capacity). It is set once and never recalculated.

**5. Events.** Every run of consecutive days with *CF < T* that lasts at least the minimum length (default 2 days) is one event. Each event records its start, end, length, minimum output and severity:

```math
Severity = \sum_{days\ in\ event}(T - CF_{day})
```

**6. Seasonal measures.** Each event is assigned to the season in which it starts. For each season the model computes the five measures defined under *Outputs*.

**7. Trend tests (each measure).** Sen's slope (median of all pairwise slopes) × 10 gives the change per decade, with a 95% range. The Mann-Kendall test, with the Hamed-Rao correction for runs of similar years, gives the p-value. The recent period (2014–2025) is also compared with the baseline using the Mann-Whitney test.

**8. Map.** Steps 1–7 are repeated for each grid point on its own, with its own threshold from its own baseline days. The 80 p-values are corrected with the Benjamini-Hochberg false discovery rate method.

**9. Drivers.** Each driver is averaged over the 80 points and over each season, then trend-tested as in step 7. Two further calculations:

- *Link (all drivers):* both the driver's seasonal series and the Dunkelflaute measure have their straight-line trends removed; the slope and correlation of a regression of one on the other measure how closely they move together year to year.
- *Effect (wind and sun only, because only they enter steps 1–3):* fit a straight line through the driver's seasonal averages. Multiply every day in season *y* by the factor below, which removes the long-term trend but keeps day-to-day weather. Rerun steps 1–7 with the same *T*.

```math
f_y = \frac{\overline{fit}}{fit(y)} \qquad Effect = 10\times\left(b_{actual} - b_{trend\ removed}\right)
```

Here *b* is the least-squares slope of the measure per year. The 95% range comes from 1,000 resamples of the seasons in 5-year blocks, re-estimating the driver's trend in each one; the Holm-corrected bootstrap p-value decides significance.

**10. Robustness checks** (result files only). The headline is rerun with: threshold at the 5th and 20th percentile; minimum length 1 and 3 days; the older and modern turbines; 70/30 and 30/70 wind/solar mixes; a weather-only index (wind *and* sunlight both below their own 20th percentile, no power conversion); and a regression on year plus NAO to control for the NAO.

## Outputs: intermediate values

Values the model calculates on the way to the results. Figures are at default settings.

| Name | Unit | Definition | Typical value |
| --- | --- | --- | --- |
| Wind capacity factor | share of capacity (0–1) | Step 1 output for one point and day | 0 to 1 |
| Solar capacity factor | share of capacity (0–1) | Step 2 output for one point and day | about 0.02 on a winter day to 0.18 on a summer day |
| Combined output (CF) | share of capacity (0–1) | Step 3: regional average of the wind/solar mix | 0.183 average over 1984–2025 |
| Threshold (*T*) | share of capacity | Step 4: the cut-off for a low day | 0.086 |
| Low day | yes/no | A day with CF below *T* | 10% of baseline days by construction |
| Event | record | Step 5: a run of at least the minimum number of low days | 339 events in 1984–2025 |

**Fields of an event record:**

| Field | Unit | Meaning |
| --- | --- | --- |
| `start` | date | First low day |
| `end` | date | Last low day |
| `length` | days | Number of consecutive low days |
| `severity` | capacity-factor-days | Total shortfall below *T* (step 5). A 3-day event sitting 0.05 below the threshold each day has severity 0.15 |
| `min_cf` | share of capacity | Lowest daily output during the event |

## Outputs: the five seasonal measures

One value per season (winter or year). Each event counts in the season in which it starts.

| Measure | Unit | Definition | Winter average (range) | Full-year average (range) |
| --- | --- | --- | --- | --- |
| **Event count** | events | Number of events starting in the season. Measures *frequency* | 5.5 (3–10) | 8.1 (4–14) |
| **Mean event length** | days | Average length of the season's events. Measures *typical length* | 3.1 (2.3–4.7) | 3.0 (2.4–4.0) |
| **Longest event** | days | Length of the season's longest event | 5.2 (3–10) | 5.6 (3–10) |
| **Total Dunkelflaute days** | days | Sum of the lengths of the season's events. Combines frequency and length | 17.2 (7–31) | 24.1 (10–46) |
| **Severity** | capacity-factor-days | Sum of the season's event severities. Measures how deep the shortfall was | 0.48 (0.13–1.00) | 0.60 (0.19–1.17) |

A season with no events would have count, longest event, total days and severity of 0 and no mean length; every season in 1984–2025 had at least 3 events.

## Outputs: dashboard

Every element on the Dashboard tab, top to bottom. "Measure" means the measure chosen in the sidebar. Results are at default settings (winter); full-year values in brackets where they differ.

The line under the page title gives the data period (NASA POWER, 1984–2025) and the baseline (1984–2013), which sets the low-output cut-off and the "before" period in comparisons.

### Headline cards

| Card | Value shown | Calculation | Subtext | Default result |
| --- | --- | --- | --- | --- |
| **Dunkelflaute frequency** · events per *season* | Change in event count, events per decade | Sen's slope of event count × 10. Always uses event count, whatever the measure | Significance tag and the Mann-Kendall p-value | +0.00 events per decade, p = 0.927 (full year: +0.00, p = 0.624) |
| **Dunkelflaute event length** · average days per event, each *season* | Change in mean event length, days per decade | Sen's slope of mean event length × 10. Always uses mean length | As above | −0.05 days per decade, p = 0.451 (full year: −0.03, p = 0.594) |
| **Locations with a significant trend** | "*n* rising · *m* falling" | Number of the 80 grid location cells (1° squares) whose own trend in the measure is significant after false discovery rate (FDR) correction | "of 80 grid location cells (after FDR)" | 0 rising · 1 falling (full year: 0 rising · 2 falling) |
| **Driver effects** | Each significant direct-driver effect, e.g. "Wind +1.1 · Sun −0.9"; "None" if neither is significant | Effect from step 9, in the measure's units per decade; shown only if significant after Holm correction | The measure, per decade | None (full year: Wind +1.1 · Sun −0.9) |

**Season tag.** The purple tag (winter or year) in the first two card labels shows the current **Season** setting. The same tag appears under the Season control in the sidebar, and all copies change together.

**Colours.**

| Colour | Where | Meaning |
| --- | --- | --- |
| Grey tag | Cards 1–2 | Not significant |
| Red | Cards 1–2 tag; card 3 "rising" | Significant and rising: more or longer Dunkelflaute |
| Blue | Cards 1–2 tag; card 3 "falling" | Significant and falling |
| Faded grey | Card 3 | A count of zero |

**Hover on card 3.** Hovering over the card lists each significant location: the nearest reference city ("near *city*" within 40 km, otherwise the distance to it), the cell's centre coordinates, and its change per decade in the chosen measure. At default settings: winter, 50 km from Hanover (52.5°N, 9.0°E), −0.40 days per decade; full year, near Saarbrücken (49.5°N, 7.0°E), −2.22, and near Aachen (50.5°N, 6.0°E), −2.11. A footnote explains FDR: a correction for testing 80 locations at once.

### Time series

| Element | Meaning |
| --- | --- |
| Blue bars | The measure for each season |
| Black dashed line | Sen's slope trend line; the legend gives the slope per decade and p-value |
| Solid blue line | 10-year centred average of the bars |
| Grey shaded block | The baseline period, 1984–2013 |
| Orange solid line (driver switched off) | 10-year average of the measure recalculated with that driver's long-term trend removed |
| Orange dashed line (driver switched off) | Sen's slope trend of that recalculated measure |
| Caption | Recent (2014–2025) average vs baseline average, their ratio, the Mann-Whitney p-value for the difference, and the 95% range of Sen's slope |

### Map: "Where is it changing?"

A line under the heading names what is mapped, for example "Change in total Dunkelflaute days per decade, winter, at each of 80 grid location cells (1° squares)". It follows the Measure and Season settings.

| Element | Meaning |
| --- | --- |
| Key: colour scale | Blue to red, labelled "Fewer", "No change" and "More", with the end values and units (for example days per decade) |
| Key: ★ | Significant trend after false discovery rate (FDR) correction |
| Key: black dot | City, for orientation |
| Coloured square | One grid location cell (1° × 1°). Colour = Sen's slope per decade of the measure there |
| ★ on a square | That cell's trend is significant after FDR correction |
| City dot and name | Hamburg, Berlin, Cologne, Munich, for orientation only |
| Hover on a square | Nearest city, coordinates, change per decade with units, p-value, and whether the cell is significant |

### Driver bars: "Why is it changing?"

| Element | Meaning |
| --- | --- |
| Bar length | Driver effect (step 9) in the measure's units per decade. Positive = the driver's long-term change added to the measure; negative = it reduced it |
| Line through the bar | 95% bootstrap range of the effect |
| Bar colour | Blue = significant after Holm correction; grey = not significant |

### Driver table

One row per driver. Drivers are regional averages over the 80 points, then averaged (or, for high-pressure days, counted) over each season.

| Driver | Unit | Definition |
| --- | --- | --- |
| Wind speed at 100 m | m/s | 50 m wind scaled to 100 m (step 1), seasonal mean |
| Surface solar irradiance | kWh/m²/day | Daily sunlight, seasonal mean |
| Cloud cover | % | Seasonal mean cloud amount |
| High-pressure days | days | Days per season meeting the high-pressure definition (fixed assumptions) |
| Temperature (2 m) | °C | Seasonal mean temperature |
| NAO index | index | Seasonal mean of the monthly NAO |

| Column | Meaning |
| --- | --- |
| Trend /decade | Sen's slope of the driver's seasonal series × 10 |
| Trend p | Mann-Kendall p-value of that trend |
| Link to *measure* | Slope of a regression of the detrended measure on the detrended driver: how much the measure changes, in its own units, for a 1-unit rise in the driver, from year-to-year variation alone |
| Link p | p-value of that regression slope |
| Trend × link | Trend /decade × link: a rough estimate of the driver's contribution per decade, used for drivers without a counterfactual effect |

The note under the table explains that sunlight and cloud come from two satellite records, GEWEX SRB up to 2000 and CERES from 2001. NASA advises against trend analysis across that switch, so the sun and cloud trends, and the sun driver effect, may partly reflect the change in source rather than the weather. Wind, temperature and pressure come from MERRA-2 throughout and are not affected.

### Event explorer

| Element | Meaning |
| --- | --- |
| Bubble chart | Every event in the chosen season type. Horizontal position = start date, height = length in days, size = severity |
| Event selector | Choose one of the 25 most severe events |
| Detail chart: black line | Daily combined output (CF) from 10 days before to 10 days after the event |
| Detail chart: dotted line | The threshold *T* |
| Detail chart: orange band | The event's days |
| Detail chart: blue and orange lines (right axis) | Regional wind at 100 m (m/s) and sunlight (kWh/m²/day) |

### Findings summary

A generated paragraph restating the frequency and length trends with their p-values, the recent vs baseline averages of the measure, and the count of significant grid points, for the current settings.

### Other tabs

**Definitions** (plain-language terms) and **Method & data** (a short technical summary). These are static text and do not change with the settings.

## Outputs: statistical terms

How to read the statistics wherever they appear.

| Term | Meaning | How to read it |
| --- | --- | --- |
| **per decade** | A trend expressed as change over 10 years (slope per year × 10) | "+1.0 days per decade" = about 4 more days over the 42 years |
| **Sen's slope** | Median of the slopes between every pair of seasons | The size of the trend; little affected by one unusual year |
| **95% range** | For Sen's slope: the range of plausible slopes. For driver effects: the middle 95% of 1,000 bootstrap results | If it includes 0, no change is a plausible answer |
| **p-value** | From the Mann-Kendall test (Hamed-Rao corrected): the chance of a trend at least this strong if there were really no trend | Small = unlikely to be chance |
| **significant** | p-value below 0.05 | Confident there is a real trend in that direction |
| **not significant** | p-value of 0.05 or more | The change cannot be separated from natural year-to-year variation. It does not prove there is no change |
| **Mann-Whitney p** | Tests whether recent seasons differ from baseline seasons | Small = the two periods really differ |
| **ratio** | Recent average ÷ baseline average | 0.89 = recent seasons average 11% less |
| **FDR (false discovery rate)** | Correction applied when testing all 80 grid points | Stops about 4 of 80 points looking significant by luck |
| **Holm correction** | Correction applied when testing both drivers | Same purpose, for two tests |
| **Bootstrap** | Re-running the calculation on 1,000 reshuffled sets of seasons (in 5-year blocks) | Shows how much a result could vary with a different run of weather |

## Outputs: result files

`python scripts/run_analysis.py` writes these to `results/` at default settings. Each file exists twice: `_winter` and `_year`. Files marked † use total Dunkelflaute days as the measure.

| File | One row per | Contents |
| --- | --- | --- |
| `events_*.csv` | event | `start`, `end`, `length`, `severity`, `min_cf` (see event record fields) |
| `metrics_*.csv` | season | `year` plus the five measures: `count`, `mean_len`, `max_len`, `total_days`, `severity` |
| `headline_*.csv` | measure | Trend and comparison statistics for each of the five measures (columns below) |
| `robustness_*.csv` † | variant | `variant` name, `threshold_cf` used, `mean` of the measure, then the trend columns below |
| `per_cell_*.csv` † | grid point | `pid` (`lat_lon`), `lat`, `lon`, `slope_decade`, `p`, `mean`, `significant_fdr`, `significant_raw` (p < 0.05 before correction) |
| `drivers_*.csv` † | driver | Driver trends and links (columns below) |
| `attribution_*.csv` † | direct driver | Driver effects (columns below) |
| `counterfactual_*.csv` † | season | `year`, `actual`, and the measure with the `wind_hub` or `ghi` trend removed |
| `drivers_yearly_*.csv` | season | `year` and each driver's seasonal value |
| `summary.json` | season type | `threshold_cf` (*T*) and `n_events` (all events in 1984–2025) |

**Trend columns** (`headline`, `robustness`):

| Column | Meaning |
| --- | --- |
| `n` | Number of seasons |
| `slope_decade`, `ci_low`, `ci_high` | Sen's slope per decade and its 95% range |
| `intercept` | Intercept of the Sen's slope line (used to draw it) |
| `p_mk` | Mann-Kendall p-value without correction |
| `p_mk_mod` | Mann-Kendall p-value with Hamed-Rao correction (the one used for "significant") |
| `tau` | Kendall's tau: −1 (always falling) to +1 (always rising) |
| `significant`, `direction` | `p_mk_mod` < 0.05; rising, falling or no trend |

**Additional `headline` columns:**

| Column | Meaning |
| --- | --- |
| `pc_baseline_mean`, `pc_recent_mean`, `pc_ratio`, `pc_p_mannwhitney` | Baseline vs recent averages, their ratio and the Mann-Whitney p-value |
| `pettitt_year`, `pettitt_p` | Pettitt test for a single abrupt shift: first year of the new level and its p-value |
| `poisson_rate_ratio_decade`, `poisson_p` | Event count only: Poisson regression; 1.10 would mean 10% more events per decade |
| `nao_ctrl_slope_decade`, `nao_ctrl_p` | Trend per decade after controlling for the NAO (regression on year and NAO) |

**`drivers` columns:**

| Column | Meaning |
| --- | --- |
| `trend_decade`, `trend_low`, `trend_high`, `trend_p`, `trend_significant` | The driver's own Sen's slope per decade, 95% range, Mann-Kendall p-value and verdict |
| `sens_slope`, `sens_p`, `sens_r` | Link: regression slope of the detrended measure on the detrended driver, its p-value and correlation |
| `implied_contribution_decade` | `trend_decade` × `sens_slope` |

**`attribution` columns:**

| Column | Meaning |
| --- | --- |
| `reduction_decade`, `reduction_low`, `reduction_high` | The driver effect shown on the dashboard and its 95% range |
| `slope_actual_decade`, `slope_cf_decade` | Least-squares trend of the measure with the driver as it was, and with its trend removed |
| `share`, `share_low`, `share_high` | Effect as a fraction of the actual trend. Unstable when the actual trend is near zero, so not shown on the dashboard |
| `p_boot`, `p_holm`, `significant_holm` | Bootstrap p-value, Holm-corrected p-value, and the significance verdict used on the dashboard |
| `significant` | Whether the 95% range excludes zero, before correction |

## Assumptions and limitations

| Limitation | Effect on results |
| --- | --- |
| Fixed hypothetical fleet | Results describe what the weather allows, not the real German grid, which also depends on demand, imports, storage and backup plants |
| Daily data | Hour-to-hour lulls are approximated by the assumed 25% spread; very short events may be missed or shortened |
| One data source (NASA POWER) | No independent dataset (such as ERA5) has been compared yet |
| Sunlight and cloud change source on 1 January 2001 | POWER switches from GEWEX SRB to CERES SYN1deg, and NASA advises against trend analysis across the switch. The sun and cloud driver trends, and the sun driver effect, may partly reflect the switch rather than the climate; the winter cloud jump in the early 2000s is probably the same issue. The Dunkelflaute measures include sunlight, so they could be affected slightly, least in winter when sunlight contributes little. Wind, temperature and pressure come from MERRA-2 throughout and are not affected |
| Rectangular region | The grid includes parts of neighbouring countries and the North and Baltic Seas |
| 42 years of data | Rare, long events are few, so trends in the longest event are noisy; event count and total days carry the main verdict |
| Driver effects are approximate | The effect assumes the trend can be removed by rescaling each season. The wind effect rests on a borderline wind trend (p = 0.07) |
| "Not significant" | Means a change cannot be separated from natural variation over this period, not that there is no change |

## Glossary

| Term | Meaning |
| --- | --- |
| Baseline | 1984–2013, the reference period |
| Capacity factor | Power produced as a share of maximum possible power (0.30 = 30%) |
| CERES / GEWEX SRB | NASA satellite programmes measuring sunlight reaching the ground |
| Counterfactual | A recalculation of history with one driver's long-term trend removed |
| Detrended | A series with its straight-line trend subtracted, leaving only year-to-year variation |
| Driver | A weather variable that influences Dunkelflaute |
| Dunkelflaute | German for "dark doldrums": a spell of very low wind and solar output |
| Fixed fleet | The same imaginary turbines and panels used for every year, so only weather changes |
| Hub height | Height of a turbine's rotor centre |
| MERRA-2 | NASA's reanalysis of the atmosphere since 1980 |
| NAO | North Atlantic Oscillation, a pressure pattern steering Europe's winter winds |
| NASA POWER | NASA service that provides MERRA-2 and satellite data for renewable energy use |
| Percentile | The value below which a given share of observations falls; the 10th percentile is exceeded by 90% of days |
| Reanalysis | A complete historical weather record built by combining observations with a weather model |
| Season | Winter (Nov–Feb, labelled by its January year) or calendar year |

## Data acknowledgement

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program. NAO index: NOAA Climate Prediction Center.
