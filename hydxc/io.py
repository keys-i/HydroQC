"""
Input/output helpers for the Hydro QC toolkit.

This module provides small utility functions for:

* Reading time series data from CSV into a pandas DataFrame.
* Ensuring that directories for output paths exist on disk.
"""

from __future__ import annotations

import os

import pandas as pd

from hydxc.config import DataConfig


def read_ts(cfg: DataConfig) -> pd.DataFrame:
    """
    Read a time series CSV into a pandas DataFrame.

    The CSV is parsed using the input and time column specified in the
    provided configuration, and the resulting DataFrame is indexed by
    the timestamp column in ascending order.

    Parameters
    ----------
    cfg
        Configuration containing paths and column names for the input CSV.

    Returns
    -------
    pandas.DataFrame
        A DataFrame indexed by the parsed time column and sorted by index.
    """
    df = pd.read_csv(cfg.input_csv)  # type: ignore[reportGeneralTypeIssues]

    if cfg.datetime_format:
        df[cfg.time_column] = pd.to_datetime(
            df[cfg.time_column],
            format=cfg.datetime_format,
        )
    else:
        df[cfg.time_column] = pd.to_datetime(df[cfg.time_column])

    df = df.set_index(cfg.time_column).sort_index()
    return df


def ensure_dir(path: str) -> None:
    """
    Ensure that the directory for a given file path exists.

    This function creates the parent directory (and any missing
    intermediate directories) for the provided path, if it does not
    already exist. If the path has no directory component, the
    current working directory is left unchanged.

    Parameters
    ----------
    path
        File path whose parent directory should be ensured.
    """
    dir_name = os.path.dirname(path)
    if not dir_name:
        # Just a filename or current directory; nothing to create.
        return

    os.makedirs(dir_name, exist_ok=True)
