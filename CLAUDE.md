# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Event-study research project examining whether VIX drops around FOMC announcement dates (2011-2018) and whether the response differs for meetings with vs. without press conferences. MIT licensed, by Finance & Technology @ HEC Montreal.

## Build & Run Commands

This is a uv-managed Python project. All commands should be run from the repo root.

```bash
uv sync                                  # Create/update environment and install dependencies
uv run python -m src.download_vix        # Download VIX data to data/cache/
uv run python -m src.run_event_study     # Run the event-study pipeline
```

## Repository Layout

- `paper/` — LaTeX manuscript (`main.tex`), bibliography, compiled PDF
- `src/` — Python source: data download, cleaning, event study analysis
- `docs/` — Implementation notes, design choices, data dictionary
- `data/events/` — Curated FOMC event inputs (version-controlled)
- `data/cache/` — Downloaded/cached files (gitignored)
- `results/` — Generated figures and tables

## Source Modules

- `src/config.py` — Central configuration: paths, date range, window parameters, CAR horizons
- `src/download_vix.py` — Downloads and caches `^VIX` daily data via yfinance
- `src/run_event_study.py` — Main pipeline: loads data, computes log changes, validates events, builds windows

## Key Data

- `data/events/fomc_events_2011_2018.csv` — FOMC event list with columns: `date`, `has_press_conf`, `year`
- VIX daily data sourced from Yahoo Finance via `yfinance` (ticker `^VIX`)

## Methodology

- Event day **t0** = FOMC announcement calendar day
- VIX response = daily close-to-close log changes: `r_t = log(VIX_t) - log(VIX_{t-1})`
- Event windows: trading days **t = -10 to +10** around t0
- CARs computed over `(0,1)`, `(0,2)`, `(0,5)` horizons
- Press-conference effect tested via difference in means and OLS regression of CAR on press-conference indicator
