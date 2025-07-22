"""
Quality-control rules for the Hydro QC toolkit.

This module defines a small set of practical QC checks that operate on
pandas Series objects representing hydrological time series, such as
water level or rainfall. The rules are designed to be simple, fast,
and easy to interpret:

* Range check: values outside a physical / expected range.
* Stuck sensor: values that barely change over a sliding window.
* Spike MAD: spikes relative to a local Median Absolute Deviation.
* Step rate: changes between samples that are too large.
* Flag combination: merge multiple flag series into a single code.

All functions return an integer Series where ``0`` means "OK" and
non-zero codes refer to specific QC rules defined by the constants
below.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pandas import Series

# Flag codes (0 = OK, >0 = increasingly "severe"/specific).
FLAG_OK: int = 0
FLAG_RANGE: int = 1
FLAG_STUCK: int = 2
FLAG_SPIKE: int = 3
FLAG_STEP: int = 4

FlagSeries = Series  # convenience alias


def apply_range_check(series: Series, min_val: float, max_val: float) -> FlagSeries:
    """
    Apply a simple min/max range check to a numeric series.

    Values strictly below ``min_val`` or strictly above ``max_val`` are
    flagged with ``FLAG_RANGE``. NaN values are left as ``FLAG_OK``.

    Parameters
    ----------
    series
        Numeric pandas Series to check.
    min_val
        Minimum acceptable value (inclusive).
    max_val
        Maximum acceptable value (inclusive).

    Returns
    -------
    pandas.Series
        Integer Series of flags aligned to ``series.index``.
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    mask = (series < min_val) | (series > max_val)
    flags[mask] = FLAG_RANGE
    return flags


def apply_stuck_sensor(series: Series, window: int, tolerance: float) -> FlagSeries:
    """
    Flag samples where the sensor appears stuck within a sliding window.

    This rule computes a rolling max and min over a window of samples and
    flags windows where the difference is less than or equal to the given
    tolerance. Conceptually, the sensor is "stuck" if it barely moves.

    The flag is applied to all samples whose rolling window satisfies the
    stuck condition.

    Parameters
    ----------
    series
        Numeric pandas Series to check.
    window
        Window size in samples for computing max/min. Must be >= 1.
    tolerance
        Maximum allowed (max - min) over the window to consider the sensor
        "stuck".

    Returns
    -------
    pandas.Series
        Integer Series of flags aligned to ``series.index``.
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    rolling_max = series.rolling(window=window, min_periods=window).max() # pyright: ignore[reportUnknownMemberType]
    rolling_min = series.rolling(window=window, min_periods=window).min() # pyright: ignore[reportUnknownMemberType]
    stuck = (rolling_max - rolling_min).abs() <= tolerance
    flags[stuck] = FLAG_STUCK
    return flags


def _rolling_mad(x: np.ndarray) -> float:
    """
    Compute the Median Absolute Deviation (MAD) for a 1D array.

    Parameters
    ----------
    x
        One-dimensional array of numeric values.

    Returns
    -------
    float
        Median absolute deviation of ``x``.
    """
    median = np.median(x)
    return float(np.median(np.abs(x - median)))


def apply_spike_mad(series: Series, window: int, threshold: float) -> FlagSeries:
    """
    Flag spikes based on a local Median Absolute Deviation (MAD) score.

    A point is flagged with ``FLAG_SPIKE`` if its absolute deviation from
    the local median, normalised by the local MAD, exceeds ``threshold``:

    ``|x_i - median(window)| / MAD(window) > threshold``

    Small windows (fewer than 3 samples) are skipped, and windows with
    MAD equal to zero are treated as non-diagnostic (no spike flagged).

    Parameters
    ----------
    series
        Numeric pandas Series to check.
    window
        Window size (in samples) used to compute the local median and MAD.
        The effective window at the edges is truncated but must have at
        least 3 points to be considered.
    threshold
        MAD-normalised spike threshold. Larger values mean fewer points are
        flagged as spikes.

    Returns
    -------
    pandas.Series
        Integer Series of flags aligned to ``series.index``.
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    arr = series.to_numpy(dtype=float)

    half = window // 2
    n = len(arr)

    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        window_vals = arr[start:end]

        if window_vals.size < 3:
            continue

        median = float(np.median(window_vals))
        mad = _rolling_mad(window_vals)
        if mad == 0.0:
            continue

        score = abs(arr[i] - median) / mad
        if score > threshold:
            flags.iloc[i] = FLAG_SPIKE

    return flags


def apply_step_rate(series: Series, max_change_per_step: float) -> FlagSeries:
    """
    Flag samples where the change to the previous sample is too large.

    This rule looks at the absolute difference between each sample and its
    immediate predecessor. If the difference exceeds ``max_change_per_step``,
    that sample is flagged with ``FLAG_STEP``.

    Parameters
    ----------
    series
        Numeric pandas Series to check.
    max_change_per_step
        Maximum allowed absolute change between consecutive samples.

    Returns
    -------
    pandas.Series
        Integer Series of flags aligned to ``series.index``.
    """
    flags = pd.Series(FLAG_OK, index=series.index, dtype="int64")
    diff = series.diff().abs()
    mask: Series = diff > max_change_per_step # pyright: ignore[reportOperatorIssue]
    flags[mask] = FLAG_STEP
    return flags


def combine_flags(*flag_series: FlagSeries) -> FlagSeries:
    """
    Combine multiple flag series by taking the maximum flag per sample.

    The assumption is that larger flag codes represent more specific or
    more severe conditions. For each index, the combined flag is the
    elementwise maximum across all provided flag Series.

    All input Series are expected to have the same index; if a mismatch
    is detected, a ``ValueError`` is raised.

    Parameters
    ----------
    *flag_series
        One or more integer flag Series to combine.

    Returns
    -------
    pandas.Series
        Integer Series of combined flags aligned to the common index.

    Raises
    ------
    ValueError
        If no flag Series are provided, or if indices do not match.
    """
    if not flag_series:
        raise ValueError("No flag series provided")

    # Verify all indices match the first series.
    reference_index = flag_series[0].index
    for idx, fs in enumerate(flag_series[1:], start=1):
        if not fs.index.equals(reference_index): # pyright: ignore[reportUnknownMemberType]
            raise ValueError(
                f"Flag series at position {idx} has a different index "
                "and cannot be safely combined."
            )

    # Stack into a DataFrame and take row-wise max.
    frame = pd.concat(flag_series, axis=1)
    combined = frame.max(axis=1).astype("int64")
    combined.name = flag_series[0].name or "qc_flag"

    return combined
