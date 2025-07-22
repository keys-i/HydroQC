"""
Configuration models and loader for the Hydro QC toolkit.

This module defines small dataclasses that capture:

* Input data configuration (CSV path, time/value columns).
* QC rule configuration (range, stuck sensor, spike MAD, step rate).
* Output configuration (paths for flags, combined CSV, charts, summary).

It also provides a `load_config` helper that reads a YAML file and
returns a fully-populated `QCConfig` instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

import yaml


@dataclass(slots=True)
class RangeConfig:
    """Configuration for the range check QC rule."""

    enabled: bool
    min: float
    max: float


@dataclass(slots=True)
class StuckConfig:
    """Configuration for the stuck sensor QC rule."""

    enabled: bool
    window: int
    tolerance: float


@dataclass(slots=True)
class SpikeMadConfig:
    """Configuration for the spike detection (MAD-based) QC rule."""

    enabled: bool
    window: int
    threshold: float


@dataclass(slots=True)
class StepConfig:
    """Configuration for the step-rate QC rule."""

    enabled: bool
    max_change_per_step: float


@dataclass(slots=True)
class DataConfig:
    """Configuration for input data and time-series parsing."""

    input_csv: str
    time_column: str
    value_column: str
    rainfall_column: Optional[str]
    datetime_format: Optional[str]
    timezone: Optional[str]


@dataclass(slots=True)
class OutputConfig:
    """Configuration for QC outputs (files and labels)."""

    flags_csv: str
    combined_csv: str
    charts_dir: str
    report_path: str
    station_name: str


@dataclass(slots=True)
class QCConfig:
    """Top-level QC configuration, as loaded from YAML."""

    data: DataConfig
    range_check: RangeConfig
    stuck_sensor: StuckConfig
    spike_mad: SpikeMadConfig
    step_rate: StepConfig
    output: OutputConfig


def _require_section(raw: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """Return a mapping for a required top-level section or raise a KeyError."""
    try:
        section= raw[key]
    except KeyError as exc:
        raise KeyError(f"Missing required top-level section '{key}' in config") from exc

    if not isinstance(section, Mapping):
        raise TypeError(f"Config section '{key}' must be a mapping/dict")

    return section # pyright: ignore[reportUnknownVariableType]


def load_config(path: str) -> QCConfig:
    """
    Load QC configuration from a YAML file.

    The YAML file is expected to contain three top-level mappings:

    * ``data``   – parsed into :class:`DataConfig`
    * ``qc``     – parsed into the various rule configs
    * ``output`` – parsed into :class:`OutputConfig`

    Parameters
    ----------
    path
        Filesystem path to the YAML configuration file.

    Returns
    -------
    QCConfig
        Parsed configuration object suitable for passing into the QC
        pipeline.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    KeyError
        If required sections or keys are missing in the YAML.
    TypeError
        If sections are not mappings/dicts as expected.
    yaml.YAMLError
        If the YAML file cannot be parsed.
    """
    with open(path, "r", encoding="utf-8") as file:
        raw: Any = yaml.safe_load(file)

    if not isinstance(raw, Mapping):
        raise TypeError("Top-level config must be a mapping/dict")

    data_section = _require_section(raw, "data") # pyright: ignore[reportUnknownArgumentType]
    qc_section = _require_section(raw, "qc") # pyright: ignore[reportUnknownArgumentType]
    out_section = _require_section(raw, "output") # pyright: ignore[reportUnknownArgumentType]

    range_section = _require_section(qc_section, "range_check")
    stuck_section = _require_section(qc_section, "stuck_sensor")
    spike_section = _require_section(qc_section, "spike_mad")
    step_section = _require_section(qc_section, "step_rate")

    data_cfg = DataConfig(
        input_csv=str(data_section["input_csv"]),
        time_column=str(data_section["time_column"]),
        value_column=str(data_section["value_column"]),
        rainfall_column=data_section.get("rainfall_column"),
        datetime_format=data_section.get("datetime_format"),
        timezone=data_section.get("timezone"),
    )

    range_cfg = RangeConfig(
        enabled=bool(range_section["enabled"]),
        min=float(range_section["min"]),
        max=float(range_section["max"]),
    )

    stuck_cfg = StuckConfig(
        enabled=bool(stuck_section["enabled"]),
        window=int(stuck_section["window"]),
        tolerance=float(stuck_section["tolerance"]),
    )

    spike_cfg = SpikeMadConfig(
        enabled=bool(spike_section["enabled"]),
        window=int(spike_section["window"]),
        threshold=float(spike_section["threshold"]),
    )

    step_cfg = StepConfig(
        enabled=bool(step_section["enabled"]),
        max_change_per_step=float(step_section["max_change_per_step"]),
    )

    output_cfg = OutputConfig(
        flags_csv=str(out_section["flags_csv"]),
        combined_csv=str(out_section["combined_csv"]),
        charts_dir=str(out_section["charts_dir"]),
        report_path=str(out_section["report_path"]),
        station_name=str(out_section["station_name"]),
    )

    return QCConfig(
        data=data_cfg,
        range_check=range_cfg,
        stuck_sensor=stuck_cfg,
        spike_mad=spike_cfg,
        step_rate=step_cfg,
        output=output_cfg,
    )
