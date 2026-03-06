"""Unit tests for event-study functions."""

import numpy as np
import pandas as pd
import pytest

from src.run_event_study import (
    build_event_windows,
    compute_all_cars,
    compute_car,
    descriptive_stats_table,
    validate_events,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def vix_df():
    """Create a synthetic VIX DataFrame spanning 30 trading days."""
    dates = pd.bdate_range("2015-01-02", periods=30, freq="B")
    # Deterministic close prices: start at 20, small daily moves
    np.random.seed(42)
    closes = 20.0 + np.cumsum(np.random.randn(30) * 0.5)
    df = pd.DataFrame({"Close": closes}, index=dates)
    df.index.name = "Date"
    df["log_change"] = np.log(df["Close"]) - np.log(df["Close"].shift(1))
    return df


@pytest.fixture()
def events_df():
    """Events that align with the synthetic VIX trading days."""
    # Pick dates within the vix_df range; day 15 (index ~14) gives room
    # for a window of +/-10 only if the series is long enough.
    # With 30 days, index 14 has start=4, end=24 -> valid.
    dates = pd.bdate_range("2015-01-02", periods=30, freq="B")
    return pd.DataFrame({
        "date": [dates[14], dates[15]],
        "has_press_conf": [1, 0],
        "year": [2015, 2015],
    })


@pytest.fixture()
def simple_window():
    """A small event window for CAR tests."""
    return pd.DataFrame({
        "event_time": list(range(-2, 4)),
        "log_change": [0.01, -0.02, 0.03, 0.04, -0.01, 0.02],
    })


# ---------------------------------------------------------------------------
# Tests: validate_events
# ---------------------------------------------------------------------------

class TestValidateEvents:
    def test_valid_dates(self, vix_df, events_df):
        result = validate_events(events_df, vix_df)
        assert "valid" in result.columns
        assert result["valid"].all()

    def test_invalid_date(self, vix_df):
        # A Saturday is never a trading day
        events = pd.DataFrame({
            "date": [pd.Timestamp("2015-01-03")],  # Saturday
            "has_press_conf": [0],
            "year": [2015],
        })
        result = validate_events(events, vix_df)
        assert not result["valid"].iloc[0]

    def test_mixed_valid_invalid(self, vix_df):
        dates = pd.bdate_range("2015-01-02", periods=30, freq="B")
        events = pd.DataFrame({
            "date": [dates[5], pd.Timestamp("2015-01-03")],
            "has_press_conf": [1, 0],
            "year": [2015, 2015],
        })
        result = validate_events(events, vix_df)
        assert result["valid"].iloc[0]
        assert not result["valid"].iloc[1]

    def test_does_not_mutate_input(self, vix_df, events_df):
        original_cols = list(events_df.columns)
        validate_events(events_df, vix_df)
        assert list(events_df.columns) == original_cols


# ---------------------------------------------------------------------------
# Tests: build_event_windows
# ---------------------------------------------------------------------------

class TestBuildEventWindows:
    def test_window_length(self, vix_df, events_df):
        events = validate_events(events_df, vix_df)
        windows = build_event_windows(events, vix_df)
        expected_len = 10 + 10 + 1  # WINDOW_PRE to WINDOW_POST inclusive
        for w in windows.values():
            assert len(w) == expected_len

    def test_event_time_range(self, vix_df, events_df):
        events = validate_events(events_df, vix_df)
        windows = build_event_windows(events, vix_df)
        for w in windows.values():
            assert w["event_time"].min() == -10
            assert w["event_time"].max() == 10

    def test_skips_invalid_events(self, vix_df):
        events = pd.DataFrame({
            "date": [pd.Timestamp("2015-01-03")],  # Saturday
            "has_press_conf": [0],
            "year": [2015],
        })
        events = validate_events(events, vix_df)
        windows = build_event_windows(events, vix_df)
        assert len(windows) == 0

    def test_skips_events_too_close_to_boundary(self, vix_df):
        # First trading day: window would extend before the start
        dates = pd.bdate_range("2015-01-02", periods=30, freq="B")
        events = pd.DataFrame({
            "date": [dates[2]],  # too close to start for window of -10
            "has_press_conf": [1],
            "year": [2015],
        })
        events = validate_events(events, vix_df)
        windows = build_event_windows(events, vix_df)
        assert len(windows) == 0

    def test_keys_are_date_strings(self, vix_df, events_df):
        events = validate_events(events_df, vix_df)
        windows = build_event_windows(events, vix_df)
        for key in windows:
            # Should be YYYY-MM-DD format
            pd.Timestamp(key)  # should not raise
            assert len(key) == 10


# ---------------------------------------------------------------------------
# Tests: compute_car
# ---------------------------------------------------------------------------

class TestComputeCar:
    def test_single_day_horizon(self, simple_window):
        # CAR(0,0) = log_change at event_time 0
        car = compute_car(simple_window, (0, 0))
        assert car == pytest.approx(0.03)

    def test_multi_day_horizon(self, simple_window):
        # CAR(0,1) = sum of event_time 0 and 1
        car = compute_car(simple_window, (0, 1))
        assert car == pytest.approx(0.03 + 0.04)

    def test_full_range(self, simple_window):
        car = compute_car(simple_window, (-2, 3))
        expected = sum([0.01, -0.02, 0.03, 0.04, -0.01, 0.02])
        assert car == pytest.approx(expected)

    def test_pre_event_horizon(self, simple_window):
        car = compute_car(simple_window, (-2, -1))
        assert car == pytest.approx(0.01 + (-0.02))

    def test_empty_horizon_returns_zero(self):
        window = pd.DataFrame({
            "event_time": [0, 1, 2],
            "log_change": [0.01, 0.02, 0.03],
        })
        # Horizon outside the window
        car = compute_car(window, (5, 10))
        assert car == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: compute_all_cars
# ---------------------------------------------------------------------------

class TestComputeAllCars:
    def test_output_shape(self, simple_window):
        windows = {"2015-01-20": simple_window}
        horizons = [(0, 1), (0, 2)]
        cars = compute_all_cars(windows, horizons)
        assert cars.shape == (1, 2)
        assert "CAR(0,1)" in cars.columns
        assert "CAR(0,2)" in cars.columns

    def test_values_match_compute_car(self, simple_window):
        windows = {"2015-01-20": simple_window}
        horizons = [(0, 1), (0, 2)]
        cars = compute_all_cars(windows, horizons)
        expected_01 = compute_car(simple_window, (0, 1))
        expected_02 = compute_car(simple_window, (0, 2))
        assert cars.loc["2015-01-20", "CAR(0,1)"] == pytest.approx(expected_01)
        assert cars.loc["2015-01-20", "CAR(0,2)"] == pytest.approx(expected_02)

    def test_multiple_events(self, simple_window):
        w2 = simple_window.copy()
        w2["log_change"] = w2["log_change"] * 2
        windows = {"2015-01-20": simple_window, "2015-01-21": w2}
        cars = compute_all_cars(windows, [(0, 1)])
        assert len(cars) == 2

    def test_empty_windows(self):
        cars = compute_all_cars({}, [(0, 1)])
        assert len(cars) == 0


# ---------------------------------------------------------------------------
# Tests: descriptive_stats_table
# ---------------------------------------------------------------------------

class TestDescriptiveStatsTable:
    def test_has_expected_groups(self, vix_df, events_df):
        events = validate_events(events_df, vix_df)
        windows = build_event_windows(events, vix_df)
        stats = descriptive_stats_table(windows, events)
        groups = stats["Group"].tolist()
        assert "All" in groups
        assert "Press Conf" in groups
        assert "No Press Conf" in groups

    def test_n_matches_events(self, vix_df, events_df):
        events = validate_events(events_df, vix_df)
        windows = build_event_windows(events, vix_df)
        stats = descriptive_stats_table(windows, events)
        all_row = stats[stats["Group"] == "All"].iloc[0]
        assert all_row["N"] == len(windows)

    def test_columns(self, vix_df, events_df):
        events = validate_events(events_df, vix_df)
        windows = build_event_windows(events, vix_df)
        stats = descriptive_stats_table(windows, events)
        for col in ["Group", "N", "Mean", "Std", "Min", "Median", "Max"]:
            assert col in stats.columns


# ---------------------------------------------------------------------------
# Tests: log change computation
# ---------------------------------------------------------------------------

class TestLogChange:
    def test_log_change_formula(self):
        dates = pd.bdate_range("2020-01-02", periods=3, freq="B")
        df = pd.DataFrame({"Close": [20.0, 21.0, 19.5]}, index=dates)
        df.index.name = "Date"
        df["log_change"] = np.log(df["Close"]) - np.log(df["Close"].shift(1))
        assert np.isnan(df["log_change"].iloc[0])
        assert df["log_change"].iloc[1] == pytest.approx(np.log(21.0 / 20.0))
        assert df["log_change"].iloc[2] == pytest.approx(np.log(19.5 / 21.0))

    def test_log_change_symmetry(self):
        # log(a/b) = -log(b/a)
        a, b = 25.0, 22.0
        assert np.log(a / b) == pytest.approx(-np.log(b / a))
