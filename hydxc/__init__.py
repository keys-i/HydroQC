"""
Public interface for the Hydro QC toolkit package.

This package provides utilities for running quality control on
hydrological time series (such as water level and rainfall),
including:

* Dataclasses for configuration (input, QC rules, outputs).
* Helpers for reading time series CSVs into pandas.
* Implementations of QC rules (range, stuck sensor, spike, step rate).
* Plotting and report helpers used by the CLI.

Most users will interact with the command-line entry point
``hydxc``. The symbols re-exported here are intended for
programmatic use in tests, notebooks, or downstream tooling.
"""

from __future__ import annotations

from importlib import metadata
from typing import List

from hydxc.config import (
    DataConfig,
    QCConfig,
    RangeConfig,
    SpikeMadConfig,
    StepConfig,
    StuckConfig,
)
from hydxc.io import read_ts, ensure_dir
from hydxc import rules

# Try to obtain the installed package version, falling back for dev checkouts.
try:
    __version__: str = metadata.version("hydro-qc-toolkit")
except metadata.PackageNotFoundError:  # pragma: no cover - dev fallback
    __version__ = "0.0.0+dev"

__all__: List[str] = [
    "__version__",
    # Config dataclasses
    "DataConfig",
    "QCConfig",
    "RangeConfig",
    "StuckConfig",
    "SpikeMadConfig",
    "StepConfig",
    # IO helpers
    "read_ts",
    "ensure_dir",
    # QC rules module
    "rules",
]
