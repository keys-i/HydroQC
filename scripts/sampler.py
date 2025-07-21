#!/usr/bin/env python
"""Initialise example data and config for the Hydro QC toolkit.

This script creates:

- examples/data.csv      Synthetic water level and rainfall time series.
- examples/config.yaml   YAML configuration file pointing to the sample data.

It is intended as a convenience for quickly bootstrapping a new checkout of the
repository with realistic-looking example inputs.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random
from typing import Any

import numpy as np
import pandas as pd
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


DEFAULT_CONFIG: dict[str, Any] = {
    "data": {
        "input_csv": "examples/data.csv",
        "time_column": "timestamp",
        "value_column": "water_level_m",
        "rainfall_column": "rain_mm",
        "datetime_format": "%Y-%m-%d %H:%M:%S",
        "timezone": "Australia/Brisbane",
    },
    "qc": {
        "range_check": {
            "enabled": True,
            "min": 0.0,
            "max": 10.0,
        },
        "stuck_sensor": {
            "enabled": True,
            "window": 6,
            "tolerance": 0.001,
        },
        "spike_mad": {
            "enabled": True,
            "window": 9,
            "threshold": 6.0,
        },
        "step_rate": {
            "enabled": True,
            "max_change_per_step": 0.3,
        },
    },
    "output": {
        "flags_csv": "out/flags.csv",
        "combined_csv": "out/qc_output.csv",
        "charts_dir": "out/charts",
        "report_path": "out/summary.md",
        "station_name": "Creek XYZ - Node 01",
    },
}


def generate_sample_data(
    path: Path,
    n_points: int = 96,
    dt_minutes: int = 15,
    start_time: datetime | None = None,
    seed: int | None = None,
) -> None:
    """Generate synthetic hydrological time series data.

    The generated data includes:

    - A "water_level_m" series with a small trend, random noise, and a couple of
      injected spikes so that QC rules have something to find.
    - A "rain_mm" series with mostly zeros and occasional bursts of rainfall.

    Parameters
    ----------
    path:
        File path where the CSV will be written.
    n_points:
        Number of samples to generate.
    dt_minutes:
        Time step between samples, in minutes.
    start_time:
        Optional starting datetime. If omitted, midnight of the current day is
        used.
    seed:
        Optional random seed for reproducible data.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    if start_time is None:
        today = datetime.now().date()
        start_time = datetime(today.year, today.month, today.day)

    timestamps = [
        start_time + timedelta(minutes=dt_minutes * i) for i in range(n_points)
    ]

    base_level = 0.8
    trend = np.linspace(0.0, 0.3, n_points)
    noise = np.random.normal(loc=0.0, scale=0.02, size=n_points)
    water_level = base_level + trend + noise

    if n_points > 20:
        water_level[20] += 2.5
    if n_points > 50:
        water_level[50] -= 1.5

    rainfall = np.zeros(n_points)
    for i in range(0, n_points, 16):
        if random.random() < 0.4:
            burst_len = random.randint(1, 4)
            burst_vals = np.random.gamma(
                shape=1.5,
                scale=2.0,
                size=burst_len,
            )
            rainfall[i : i + burst_len] = burst_vals

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "water_level_m": water_level,
            "rain_mm": rainfall,
        }
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

    table = Table(title="Sample data written")
    table.add_column("Column")
    table.add_column("Example values", overflow="fold")

    for col in df.columns:
        sample_vals = df[col].head(5).to_list()
        table.add_row(col, str(sample_vals))

    console.print(table)


def write_config(path: Path, config: dict[str, Any]) -> None:
    """Write a YAML configuration file.

    Parameters
    ----------
    path:
        File path where the YAML configuration will be written.
    config:
        Configuration dictionary to serialise to YAML.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, sort_keys=False)

    console.print(
        Panel.fit(
            f"Config written to [bold]{path}[/bold]",
            title="Config",
        )
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Initialise example data and config for the Hydro QC toolkit.\n\n"
            "Creates:\n"
            "  - examples/data.csv  (synthetic water level + rainfall)\n"
            "  - examples/config.yaml  (QC configuration template)\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--examples-dir",
        type=str,
        default="examples",
        help="Directory to write examples into (default: examples).",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=96,
        help=(
            "Number of data points to generate "
            "(default: 96, approximately one day at 15 minutes)."
        ),
    )
    parser.add_argument(
        "--dt-minutes",
        type=int,
        default=15,
        help="Time step between points in minutes (default: 15).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sample data (default: 42).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing data.csv and config.yaml if they exist.",
    )

    return parser.parse_args()


def main() -> None:
    """Entry point for the example initialisation script.

    This function orchestrates argument parsing, data generation, and writing of
    the configuration file. It also prints a summary of next steps for running
    the QC CLI.
    """
    args = parse_args()

    examples_dir = Path(args.examples_dir)
    data_path = examples_dir / "data.csv"
    config_path = examples_dir / "config.yaml"

    console.print(
        Panel.fit(
            f"Initialising examples in [bold]{examples_dir}[/bold]",
            title="Hydro QC examples",
        )
    )

    if not args.overwrite:
        for candidate in (data_path, config_path):
            if candidate.exists():
                console.print(
                    f"[red]Error:[/red] {candidate} already exists. "
                    "Use --overwrite to replace it."
                )
                return

    console.print(
        f"Generating sample data: [bold]{data_path}[/bold]\n"
        f"  points={args.points}, dt={args.dt_minutes} minutes, "
        f"seed={args.seed}"
    )
    generate_sample_data(
        path=data_path,
        n_points=args.points,
        dt_minutes=args.dt_minutes,
        seed=args.seed,
    )

    console.print(f"\nWriting config: [bold]{config_path}[/bold]")

    config = dict(DEFAULT_CONFIG)
    data_cfg = dict(config["data"])
    output_cfg = dict(config["output"])

    data_cfg["input_csv"] = str(data_path)
    config["data"] = data_cfg

    output_cfg["flags_csv"] = "out/flags.csv"
    output_cfg["combined_csv"] = "out/qc_output.csv"
    output_cfg["charts_dir"] = "out/charts"
    output_cfg["report_path"] = "out/summary.md"
    config["output"] = output_cfg

    write_config(config_path, config)

    next_steps = (
        "\nYou can now run your QC tool with, for example:\n\n"
        "  hydxc -c examples/config.yaml\n\n"
        "or:\n\n"
        "  python -m hydxc.cli -c examples/config.yaml\n"
    )

    console.print(
        Panel.fit(
            next_steps,
            title="Next steps",
        )
    )


if __name__ == "__main__":
    main()
