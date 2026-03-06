# FOMC Announcements and VIX (2011–2018): Event Study with Press Conference Split

This repository contains an event-study project that examines whether the VIX index tends to drop around FOMC announcement dates from 2011 to 2018, and whether the response differs between meetings that include a press conference versus those that do not.

## Research Question

1. **Baseline:** Does VIX decline around FOMC announcements?
2. **Main question:** Is any decline different for FOMC announcements with press conferences vs without press conferences?

## Data

- **VIX:** Daily VIX from Yahoo Finance via `yfinance` (ticker `^VIX`).
- **FOMC events:** A curated event table (CSV) listing FOMC announcement dates and whether the meeting had a press conference.

## Timing Convention (Fixed)

- Event day **t0** is the calendar day of the FOMC announcement.
- VIX response is measured using daily close-to-close log changes:
  \[
  r_t = \log(\text{VIX}_t) - \log(\text{VIX}_{t-1})
  \]
- Event windows are constructed in trading days from **t = -10 to +10** around t0.

## Method Overview

1. Load the event list (2011–2018) and press-conference indicator.
2. Download VIX daily data and compute daily log changes.
3. For each event, construct an event window from **t = -10 to +10** trading days.
4. Compute:
   - Average log change in VIX by event time (event-study plot)
   - Cumulative changes (CAR) over selected horizons:
     - `CAR(0,1)`, `CAR(0,2)`, `CAR(0,5)` (primary)
5. Compare press-conference vs non-press-conference events using:
   - Difference in means of CARs
   - Regression of CAR on press-conference indicator:
     \[
     \text{CAR}_{i}(0,k) = \alpha + \beta \cdot \text{PressConf}_i + \varepsilon_i
     \]

## Repository Layout

- `paper/` : LaTeX manuscript (`main.tex`), bibliography, compiled PDF output
- `src/` : Python source code for data download, cleaning, and event study
- `docs/` : implementation notes (design choices, checks, data dictionary)
- `data/` :
  - `data/events/` : curated event inputs (version-controlled)
  - `data/cache/` : downloaded/cache files (gitignored)
- `results/` : generated figures and tables

## Python environment (uv)

### Install uv

If you don’t already have it, install `uv` (see the official uv docs for your OS).

### Create the project environment and install dependencies

From the repo root:

```bash
uv sync
```

### Run the pipeline

```bash
# Download VIX data (cached to data/cache/)
uv run python -m src.download_vix

# Run the event-study skeleton
uv run python -m src.run_event_study
```
