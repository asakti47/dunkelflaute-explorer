# Dunkelflaute Explorer

**NASA Space Apps Challenge 2026: Be An Earth System Trend Detective!**

Is *Dunkelflaute* (German for "dark doldrums": long spells with little wind **and** little sun) becoming more frequent or longer over Germany, where is it changing, and why?

## What we found (NASA POWER data, 1984–2025, 80 grid points)

- **No significant trend in frequency or length.** Winter Dunkelflaute averaged 17.8 days per winter in 1984–2013 and 15.8 in 2014–2025 (Mann-Whitney p = 0.39). Mann-Kendall trends for event count, mean length, longest event, total days and severity are all non-significant (p = 0.45–0.93). The verdict holds across 10 variants of the definition (thresholds, durations, turbines, wind/solar mix, a weather-only index) and after controlling for the North Atlantic Oscillation.
- **Extremes still happen.** The detector finds the well-known events of January 2017 and November–December 2024. **4–13 November 2024 is the most severe event in the 42-year record.**
- **Opposite trends in different places.** The map shows falling Dunkelflaute in western Germany and rising in the east; only one cell is significant after false-discovery-rate correction, so the pattern is suggestive rather than proven.
- **Drivers that cancel out (full year).** Sunlight is rising significantly ("brightening", +0.08 kWh/m²/day per decade, p < 0.001) while wind at hub height is slightly falling (−0.06 m/s per decade, p = 0.07, borderline). Re-running history without each trend: brightening **removed** about −0.9 Dunkelflaute days per decade (95% range −1.3 to −0.5), and the wind decline **added** about +1.1 (95% range +0.4 to +3.5). The ranges include uncertainty in each driver's own trend. The sunlight effect is clear; the wind effect is likely but rests on a borderline wind trend. Together they largely offset, which is why the total shows no trend. In winter alone, neither wind nor sunlight trends significantly.
- **Data caution.** Winter cloud cover jumps around 2004 with no trend before or after, which points to a change in the satellite cloud record; we do not interpret that trend.

## How it works

1. **Data:** NASA POWER daily point data (wind and temperature from MERRA-2; sunlight and cloud from CERES SYN1deg and GEWEX SRB) on a 1° grid, 47.5–54.5°N, 6–15°E. NOAA CPC monthly NAO index.
2. **Weather → power with frozen technology:** 50 m wind scaled to 100 m, passed through a fixed turbine power curve (averaged over an assumed within-day spread); sunlight converted with a fixed panel. The same fleet is used for every year, so trends reflect weather, not new technology.
3. **Events:** regional combined output below the 10th percentile of 1984–2013 days for at least 2 days.
4. **Statistics:** Mann-Kendall (Hamed-Rao autocorrelation correction), Sen's slope with 95% CI, Mann-Whitney recent vs baseline, Poisson regression, Pettitt change-point, Benjamini-Hochberg FDR across cells.
5. **Attribution:** counterfactual runs with each driver's long-term trend removed; paired moving-block bootstrap (5-year blocks, 1,000 resamples, re-estimating each driver's trend in every resample); Holm correction.

## Run it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py          # dashboard (data are in data/)
python scripts/run_analysis.py          # writes all result tables to results/
python scripts/fetch_data.py            # re-download NASA POWER + NAO (needs internet)
python -m pytest -q tests
```

The data in `data/` were moved into the repo as base64 parts; the app rebuilds the `.csv.gz` files automatically on first run (`scripts/assemble_parts.py` does the same by hand).

## Data acknowledgement

These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program. NAO index: NOAA Climate Prediction Center.

## Limitations

Daily data smooth hour-to-hour swings; one reanalysis source; a fixed hypothetical fleet rather than Germany's real one; 42 years is short for rare, long events.
