"""
Plotting helpers for the Hydro QC toolkit.

This module provides functions for generating quick-look charts of
time series data with QC flags overlaid, and saving them to disk.
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from pandas import DataFrame

from hydxc.io import ensure_dir


def plot_series_with_flags(
    df: DataFrame,
    value_column: str,
    flag_column: str,
    out_dir: str,
    station_name: str,
) -> str:
    """
    Plot a time series with QC flags overlaid and save it as a PNG file.

    The function plots the specified value column over time, highlights
    all samples with non-zero QC flags, and writes a PNG file into the
    given output directory. The path to the saved chart is returned.

    Parameters
    ----------
    df
        DataFrame containing the time series data and QC flags.
        The index is expected to be a datetime-like index.
    value_column
        Name of the column containing the numeric values to plot.
    flag_column
        Name of the column containing QC flag codes (0 = OK, non-zero = flagged).
    out_dir
        Directory in which the chart PNG file should be written.
    station_name
        Human-readable name of the station or node used in the chart title.

    Returns
    -------
    str
        The filesystem path of the saved PNG chart.
    """
    # Ensure the output directory exists.
    ensure_dir(os.path.join(out_dir, "dummy.txt"))

    fig: Figure
    ax: Axes
    fig, ax = plt.subplots(figsize=(10, 4)) # pyright: ignore[reportUnknownMemberType]

    # pandas plotting wraps matplotlib; Pylance sometimes sees this as "partially unknown".
    df[value_column].plot(ax=ax, label=value_column)  # type: ignore[reportUnknownMemberType]

    # Overlay flagged points.
    flagged = df[df[flag_column] != 0]
    if not flagged.empty:
        ax.scatter(  # type: ignore[reportUnknownMemberType]
            flagged.index,
            flagged[value_column],
            marker="x",
            label="Flagged",
        )

    ax.set_title(  # type: ignore[reportUnknownMemberType]
        f"{station_name} - {value_column} with QC flags"
    )
    ax.set_xlabel("Time")  # type: ignore[reportUnknownMemberType]
    ax.set_ylabel(value_column)  # type: ignore[reportUnknownMemberType]
    ax.legend()  # type: ignore[reportUnknownMemberType]
    fig.tight_layout()  # type: ignore[reportUnknownMemberType]

    out_path = os.path.join(out_dir, f"{value_column}_qc.png")
    fig.savefig(out_path, dpi=150)  # type: ignore[reportUnknownMemberType]
    plt.close(fig)

    return out_path
