"""Project configuration: paths, date range, event-window parameters."""

from pathlib import Path

# Project root (two levels up from this file: src/config.py -> repo root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data paths
EVENTS_CSV = PROJECT_ROOT / "data" / "events" / "fomc_events_2011_2018.csv"
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
VIX_CACHE = CACHE_DIR / "vix_daily.csv"

# Results paths
FIGURES_DIR = PROJECT_ROOT / "results" / "figures"
TABLES_DIR = PROJECT_ROOT / "results" / "tables"

# VIX download parameters
VIX_TICKER = "^VIX"
VIX_START = "2010-06-01"  # buffer before first event (2011-01-26)
VIX_END = "2019-06-01"    # buffer after last event (2018-12-19)

# Event-window parameters (in trading days)
WINDOW_PRE = -10
WINDOW_POST = 10

# CAR horizons: list of (start, end) tuples in event time
CAR_HORIZONS = [(0, 1), (0, 2), (0, 5)]
