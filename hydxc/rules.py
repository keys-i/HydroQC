from __future__ import annotations
import numpy as np
import pandas as pd

FLAG_OK = 0
FLAG_RANGE = 1
FLAG_STUCK = 2
FLAG_SPIKE = 3
FLAG_STEP = 4

def apply_range_check(series: pd.Series, min_val: float, max_val: float) -> pd.Series:
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    mask = (series < min_val) | (series > max_val)
    flags[mask] = FLAG_RANGE
    return flags

def apply_stuck_sensor(series: pd.Series, window: int, tolerance: float) -> pd.Series:
    """
    Flags points where the rolling max-min within window is below tolerance
    (i.e., sensor is basically flat / stuck).
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    rolling_max = series.rolling(window=window, min_periods=window).max()
    rolling_min = series.rolling(window=window, min_periods=window).min()
    stuck = (rolling_max - rolling_min).abs() <= tolerance
    flags[stuck] = FLAG_STUCK
    return flags

def _rolling_mad(x: np.ndarray) -> float:
    median = np.median(x)
    return np.median(np.abs(x - median))

def apply_spike_mad(series: pd.Series, window: int, threshold: float) -> pd.Series:
    """
    Flags spikes based on Median Absolute Deviation (MAD).
    A point is flagged if |x - median(window)| / MAD(window) > threshold.
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    arr = series.to_numpy(dtype=float)

    half = window // 2
    for i in range(len(arr)):
        start = max(0, i - half)
        end = min(len(arr), i + half + 1)
        window_vals = arr[start:end]
        if len(window_vals) < 3:
            continue
        median = np.median(window_vals)
        mad = _rolling_mad(window_vals)
        if mad == 0:
            continue
        score = abs(arr[i] - median) / mad
        if score > threshold:
            flags.iloc[i] = FLAG_SPIKE

    return flags

def apply_step_rate(series: pd.Series, max_change_per_step: float) -> pd.Series:
    """
    Flags points where absolute difference to previous sample exceeds max_change_per_step.
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    diff = series.diff().abs()
    mask = diff > max_change_per_step
    flags[mask] = FLAG_STEP
    return flags

def combine_flags(*flag_series: pd.Series) -> pd.Series:
    """
    Combine multiple flag series, keeping the highest flag code per point.
    """
    if not flag_series:
        raise ValueError("No flag series provided")

    combined = flag_series[0].copy()
    for fs in flag_series[1:]:
        combined = np.maximum(combined, fs)
    return combined