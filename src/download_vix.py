"""Download and cache daily VIX data from Yahoo Finance."""

import yfinance as yf

from src.config import CACHE_DIR, VIX_CACHE, VIX_END, VIX_START, VIX_TICKER


def download_vix() -> None:
    """Download VIX daily data and save to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {VIX_TICKER} from {VIX_START} to {VIX_END} ...")
    df = yf.download(VIX_TICKER, start=VIX_START, end=VIX_END, auto_adjust=True)

    if df.empty:
        raise RuntimeError("yfinance returned no data for VIX.")

    # Flatten multi-level columns if present (yfinance sometimes returns MultiIndex)
    if hasattr(df.columns, "levels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)

    df.to_csv(VIX_CACHE)
    print(f"Saved {len(df)} rows to {VIX_CACHE}")


if __name__ == "__main__":
    download_vix()
