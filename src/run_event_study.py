"""Skeleton event-study pipeline: load data, compute log changes, validate events."""

import numpy as np
import pandas as pd

from src.config import (
    CAR_HORIZONS,
    EVENTS_CSV,
    VIX_CACHE,
    WINDOW_POST,
    WINDOW_PRE,
)


def load_vix() -> pd.DataFrame:
    """Load cached VIX data and compute daily log changes."""
    if not VIX_CACHE.exists():
        raise FileNotFoundError(
            f"VIX cache not found at {VIX_CACHE}. "
            "Run 'uv run python -m src.download_vix' first."
        )
    df = pd.read_csv(VIX_CACHE, parse_dates=["Date"], index_col="Date")
    df = df.sort_index()
    # Daily log change: r_t = log(VIX_t) - log(VIX_{t-1})
    df["log_change"] = np.log(df["Close"]) - np.log(df["Close"].shift(1))
    return df


def load_events() -> pd.DataFrame:
    """Load the FOMC event table."""
    df = pd.read_csv(EVENTS_CSV, parse_dates=["date"])
    return df


def validate_events(events: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    """Check that each event date maps to a valid trading day in VIX data.

    Returns events DataFrame with an added 'valid' column and the integer
    location of each event in the VIX index.
    """
    trading_days = vix.index
    events = events.copy()
    events["valid"] = events["date"].isin(trading_days)
    return events


def build_event_windows(
    events: pd.DataFrame, vix: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """For each valid event, extract the event window of log changes.

    Returns a dict mapping event date string to a DataFrame with columns
    'event_time' and 'log_change'.
    """
    trading_days = vix.index
    windows = {}

    for _, row in events.iterrows():
        if not row["valid"]:
            continue
        t0_loc = trading_days.get_loc(row["date"])
        start = t0_loc + WINDOW_PRE
        end = t0_loc + WINDOW_POST

        if start < 0 or end >= len(trading_days):
            continue

        window = vix.iloc[start : end + 1][["log_change"]].copy()
        window["event_time"] = range(WINDOW_PRE, WINDOW_POST + 1)
        windows[str(row["date"].date())] = window

    return windows


def run() -> None:
    """Run the skeleton event-study pipeline with sanity checks."""
    # Load data
    vix = load_vix()
    events = load_events()

    print(f"VIX data: {len(vix)} trading days, "
          f"{vix.index.min().date()} to {vix.index.max().date()}")
    print(f"Events loaded: {len(events)}")

    # Validate events
    events = validate_events(events, vix)
    n_valid = events["valid"].sum()
    n_total = len(events)
    pct = n_valid / n_total * 100

    print(f"Events mapped to valid trading days: {n_valid}/{n_total} ({pct:.1f}%)")

    if not events["valid"].all():
        invalid = events.loc[~events["valid"], "date"]
        print(f"  Warning: invalid event dates: {list(invalid.dt.date)}")

    # Build event windows
    windows = build_event_windows(events, vix)
    print(f"Event windows successfully constructed: {len(windows)}/{n_valid}")

    # Summary of CAR horizons
    print(f"\nCAR horizons to compute: {CAR_HORIZONS}")
    print(f"Event window: [{WINDOW_PRE}, +{WINDOW_POST}] trading days")

    # Press-conference split summary
    pc_counts = events.loc[events["valid"], "has_press_conf"].value_counts()
    print(f"\nPress-conference split (valid events):")
    print(f"  With press conf:    {pc_counts.get(1, 0)}")
    print(f"  Without press conf: {pc_counts.get(0, 0)}")


if __name__ == "__main__":
    run()
