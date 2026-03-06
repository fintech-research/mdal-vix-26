"""Event-study pipeline: load data, compute log changes, validate events,
compute CARs, generate descriptive statistics and figures."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.config import (
    CAR_HORIZONS,
    EVENTS_CSV,
    FIGURES_DIR,
    TABLES_DIR,
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


def compute_car(
    window: pd.DataFrame, horizon: tuple[int, int]
) -> float:
    """Compute the cumulative abnormal return for a given horizon.

    Parameters
    ----------
    window : DataFrame with columns 'event_time' and 'log_change'.
    horizon : (start, end) tuple in event time, inclusive on both ends.

    Returns
    -------
    CAR as the sum of log_change over the horizon.
    """
    start, end = horizon
    mask = (window["event_time"] >= start) & (window["event_time"] <= end)
    return window.loc[mask, "log_change"].sum()


def compute_all_cars(
    windows: dict[str, pd.DataFrame],
    horizons: list[tuple[int, int]] | None = None,
) -> pd.DataFrame:
    """Compute CARs for all events and horizons.

    Returns a DataFrame indexed by event date with one column per horizon.
    """
    if horizons is None:
        horizons = CAR_HORIZONS

    records = []
    for date_str, window in windows.items():
        row = {"date": date_str}
        for h in horizons:
            row[f"CAR({h[0]},{h[1]})"] = compute_car(window, h)
        records.append(row)
    if not records:
        cols = [f"CAR({h[0]},{h[1]})" for h in horizons]
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(records).set_index("date")


def build_vix_level_panel(
    events: pd.DataFrame, vix: pd.DataFrame
) -> pd.DataFrame:
    """Build a panel of VIX levels in event time for each valid event.

    Returns a long DataFrame with columns: event_date, event_time,
    vix_close, has_press_conf, year.
    """
    trading_days = vix.index
    rows = []

    for _, ev in events.iterrows():
        if not ev["valid"]:
            continue
        t0_loc = trading_days.get_loc(ev["date"])
        start = t0_loc + WINDOW_PRE
        end = t0_loc + WINDOW_POST
        if start < 0 or end >= len(trading_days):
            continue
        for tau in range(WINDOW_PRE, WINDOW_POST + 1):
            idx = t0_loc + tau
            rows.append({
                "event_date": str(ev["date"].date()),
                "event_time": tau,
                "vix_close": vix.iloc[idx]["Close"],
                "has_press_conf": ev["has_press_conf"],
                "year": ev["year"],
            })

    return pd.DataFrame(rows)


def descriptive_stats_table(
    windows: dict[str, pd.DataFrame],
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Compute descriptive statistics of event-window log changes.

    Returns a table with rows for: All / Press Conf / No Press Conf,
    plus per-year breakdowns within each group.
    """
    # Build a flat DataFrame of per-event mean log_change in the window
    valid_events = events[events["valid"]].copy()
    valid_events["date_str"] = valid_events["date"].dt.strftime("%Y-%m-%d")

    records = []
    for _, ev in valid_events.iterrows():
        date_str = ev["date_str"]
        if date_str not in windows:
            continue
        w = windows[date_str]
        # Use the CAR(0,1) as the main return measure
        car01 = compute_car(w, (0, 1))
        records.append({
            "date": date_str,
            "has_press_conf": ev["has_press_conf"],
            "year": ev["year"],
            "CAR(0,1)": car01,
        })

    df = pd.DataFrame(records)

    def _stats(subset: pd.DataFrame, label: str) -> dict:
        vals = subset["CAR(0,1)"]
        return {
            "Group": label,
            "N": len(vals),
            "Mean": vals.mean(),
            "Std": vals.std(),
            "Min": vals.min(),
            "Median": vals.median(),
            "Max": vals.max(),
        }

    rows = []
    # Overall groups
    rows.append(_stats(df, "All"))
    rows.append(_stats(df[df["has_press_conf"] == 1], "Press Conf"))
    rows.append(_stats(df[df["has_press_conf"] == 0], "No Press Conf"))

    # By year within each group
    for year in sorted(df["year"].unique()):
        sub = df[df["year"] == year]
        rows.append(_stats(sub, f"  {year} - All"))
        pc = sub[sub["has_press_conf"] == 1]
        if len(pc) > 0:
            rows.append(_stats(pc, f"  {year} - Press Conf"))
        npc = sub[sub["has_press_conf"] == 0]
        if len(npc) > 0:
            rows.append(_stats(npc, f"  {year} - No Press Conf"))

    return pd.DataFrame(rows)


def export_stats_table(stats: pd.DataFrame) -> None:
    """Export descriptive statistics table as Markdown and LaTeX."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # Format numeric columns
    fmt = stats.copy()
    for col in ["Mean", "Std", "Min", "Median", "Max"]:
        fmt[col] = fmt[col].map(lambda x: f"{x:.4f}")
    fmt["N"] = fmt["N"].astype(int)

    # Markdown
    md_path = TABLES_DIR / "descriptive_stats.md"
    md_path.write_text(fmt.to_markdown(index=False))

    # LaTeX
    tex_path = TABLES_DIR / "descriptive_stats.tex"
    tex_path.write_text(
        fmt.to_latex(index=False, caption="Descriptive Statistics of Event-Window Returns (CAR(0,1))",
                     label="tab:desc_stats")
    )

    print(f"Table exported to {md_path} and {tex_path}")


def plot_vix_event_time(panel: pd.DataFrame) -> None:
    """Plot average VIX levels in event time, split by press conference."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    pc = panel[panel["has_press_conf"] == 1]
    npc = panel[panel["has_press_conf"] == 0]

    avg_pc = pc.groupby("event_time")["vix_close"].mean()
    avg_npc = npc.groupby("event_time")["vix_close"].mean()

    # Normalize to level at t-1
    base_pc = avg_pc.loc[-1]
    base_npc = avg_npc.loc[-1]
    avg_pc = avg_pc / base_pc * 100
    avg_npc = avg_npc / base_npc * 100

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(avg_pc.index, avg_pc.values, marker="o", markersize=4,
            label="With Press Conf", linewidth=1.5)
    ax.plot(avg_npc.index, avg_npc.values, marker="s", markersize=4,
            label="Without Press Conf", linewidth=1.5)
    ax.axvline(0, color="grey", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Event Time (trading days)")
    ax.set_ylabel("VIX Level (normalized, t\u2212\u20091 = 100)")
    ax.set_title("Average VIX Level Around FOMC Announcements")
    ax.set_xticks(range(WINDOW_PRE, WINDOW_POST + 1))
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    png_path = FIGURES_DIR / "vix_event_time.png"
    pdf_path = FIGURES_DIR / "vix_event_time.pdf"
    fig.savefig(png_path, dpi=150)
    fig.savefig(pdf_path)
    plt.close(fig)

    print(f"Figure exported to {png_path} and {pdf_path}")


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

    # Compute CARs
    cars = compute_all_cars(windows)
    print(f"\nCARs computed for {len(cars)} events:")
    print(cars.describe().round(4))

    # Descriptive statistics table
    stats = descriptive_stats_table(windows, events)
    export_stats_table(stats)

    # VIX level figure
    panel = build_vix_level_panel(events, vix)
    plot_vix_event_time(panel)


if __name__ == "__main__":
    run()
