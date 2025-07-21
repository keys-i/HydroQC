"""
Command-line interface for the Hydro QC toolkit.

This module provides a Rich-enhanced, argparse-based CLI for running
quality control checks on hydrological time series (such as water
level and rainfall). It:

* Loads configuration from a YAML file.
* Reads time series data using pandas.
* Applies a set of QC rules (range, stuck sensor, spike, step rate).
* Writes flags and combined CSVs, a chart image, and a summary report.
* Optionally renders a terminal plot using plotille.

The main entry point is :func:`main`, which is wired to the console
script ``hydro-qc`` in pyproject.toml.
"""

from __future__ import annotations

import argparse
import os
import re
from typing import Dict, Iterable, List, Tuple, Match, cast

import pandas as pd
import plotille
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich_argparse import RichHelpFormatter
from tqdm import tqdm

from hydxc.config import QCConfig, load_config
from hydxc.io import read_ts, ensure_dir
from hydxc import rules
from hydxc.plotting import plot_series_with_flags
from hydxc.report import generate_summary

# Console with a simple theme for status messages.
custom_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "bold red",
        "step": "magenta",
    }
)
console: Console = Console(theme=custom_theme)

# Map flag codes to human-readable labels.
FLAG_LABELS: Dict[int, str] = {
    rules.FLAG_OK: "OK",
    rules.FLAG_RANGE: "Range",
    rules.FLAG_STUCK: "Stuck sensor",
    rules.FLAG_SPIKE: "Spike (MAD)",
    rules.FLAG_STEP: "Step rate",
}


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser for the Hydro QC CLI.

    Returns
    -------
    argparse.ArgumentParser
        The configured argument parser instance.
    """
    parser = argparse.ArgumentParser(
        prog="hydro-qc",
        description="Hydro QC Toolkit – rainfall and water level QC.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config",
        required=True,
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars (for very quiet or non-TTY runs).",
    )
    parser.add_argument(
        "--no-chart-preview",
        action="store_true",
        help="Disable inline terminal chart preview.",
    )
    return parser


def _print_header(config_path: str) -> None:
    """
    Print a Rich panel header with basic run information.

    Parameters
    ----------
    config_path
        The path to the YAML configuration file being used.
    """
    console.print(
        Panel.fit(
            f"Hydro QC Toolkit\n\nUsing config: [bold]{config_path}[/bold]",
            title="Hydro QC",
            border_style="step",
        )
    )


def _print_dataset_summary(df: pd.DataFrame, value_col: str) -> None:
    """
    Print a short summary of the input dataset.

    Parameters
    ----------
    df
        The input time series dataframe (indexed by timestamp).
    value_col
        Name of the primary value column being QC-checked.
    """
    table = Table(title="Input dataset", show_lines=True)
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Index type", type(df.index).__name__)
    table.add_row("Samples", str(len(df)))
    if not df.empty:
        table.add_row("Start", str(df.index.min()))
        table.add_row("End", str(df.index.max()))
    table.add_row("Value column", value_col)

    console.print(table)


def _print_rule_config(cfg: QCConfig) -> None:
    """
    Print which QC rules are enabled and their key parameters.

    Parameters
    ----------
    cfg
        Parsed QC configuration dataclass instance.
    """
    table = Table(title="QC rules", show_lines=True)
    table.add_column("Rule", style="cyan", no_wrap=True)
    table.add_column("Enabled", style="white", no_wrap=True)
    table.add_column("Parameters", style="white")

    table.add_row(
        "Range check",
        "yes" if cfg.range_check.enabled else "no",
        f"min={cfg.range_check.min}, max={cfg.range_check.max}",
    )
    table.add_row(
        "Stuck sensor",
        "yes" if cfg.stuck_sensor.enabled else "no",
        f"window={cfg.stuck_sensor.window}, "
        f"tolerance={cfg.stuck_sensor.tolerance}",
    )
    table.add_row(
        "Spike MAD",
        "yes" if cfg.spike_mad.enabled else "no",
        f"window={cfg.spike_mad.window}, "
        f"threshold={cfg.spike_mad.threshold}",
    )
    table.add_row(
        "Step rate",
        "yes" if cfg.step_rate.enabled else "no",
        f"max_change_per_step={cfg.step_rate.max_change_per_step}",
    )

    console.print(table)


def _preview_chart_terminal(df: pd.DataFrame, value_col: str) -> None:
    """
    Render a coloured line plot of the series in the terminal.

    The preview uses plotille to draw a simple ASCII chart with a coloured line
    and applies Rich styling so that axis numbers are bold white.

    Parameters
    ----------
    df
        Dataframe containing the series to plot.
    value_col
        Name of the numeric column to preview.
    """
    if df.empty:
        console.print("[warning]No data available for terminal plot.[/warning]")
        return

    max_points: int = 200
    if len(df) > max_points:
        view = df.iloc[:max_points]
        truncated = True
    else:
        view = df
        truncated = False

    y_vals = view[value_col].astype(float).to_list()
    x_vals = list(range(len(y_vals)))

    fig: plotille.Figure = plotille.Figure()
    fig.width = 80
    fig.height = 20
    fig.x_label = "Sample index"
    fig.y_label = value_col
    fig.color_mode = "byte"  # enable 256-color output

    # plotille is untyped, so we ignore the "partially unknown" warning here.
    fig.set_x_limits(  # type: ignore[reportUnknownMemberType]
        min_=0,
        max_=len(x_vals) - 1,
    )
    fig.plot(  # type: ignore[reportUnknownMemberType]
        x_vals,
        y_vals,
        label=value_col,
        lc=63,  # bright-ish colour in 256-color space
    )

    # plotille's typing is loose, so cast to str for Pylance.
    plot_str: str = cast(str, fig.show(legend=True))

    console.print(
        Panel.fit(
            "Inline terminal preview (plotille, coloured).\n"
            "For higher quality, open the PNG chart written to disk.",
            title="Chart preview",
            border_style="step",
        )
    )

    text: Text = Text.from_ansi(plot_str)
    plain: str = text.plain

    # Style numeric tokens (axis numbers, tick labels) as bold white.
    for match in re.finditer(r"-?\d+(?:\.\d+)?", plain):
        match_span: Match[str] = match
        start, end = match_span.span()
        text.stylize("bold white", start, end)

    console.print(text)

    if truncated:
        console.print(
            "[warning]Preview truncated to first "
            f"{max_points} samples for readability.[/warning]"
        )


def _print_flag_summary(df: pd.DataFrame) -> None:
    """
    Print a table summarising how many points received each QC flag.

    Parameters
    ----------
    df
        Dataframe containing the ``qc_flag`` column.
    """
    if "qc_flag" not in df.columns or df.empty:
        console.print("[warning]No qc_flag column to summarise.[/warning]")
        return

    total: int = int(len(df))

    # Build a typed dict[int, int] from value_counts() in a way Pylance likes.
    value_counts = df["qc_flag"].value_counts()

    counts: Dict[int, int] = {}
    for key, count_val in value_counts.items():
        # Pylance sees key as Hashable; assert it is int-like.
        int_key = cast(int, key)
        counts[int_key] = int(count_val)

    table = Table(title="QC flag summary", show_lines=True)
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Label", style="white", no_wrap=True)
    table.add_column("Count", style="white", no_wrap=True)
    table.add_column("Percent", style="white", no_wrap=True)

    for code in sorted(FLAG_LABELS.keys()):
        label = FLAG_LABELS.get(code, f"Unknown ({code})")
        count: int = counts.get(code, 0)
        pct: float = 100.0 * count / total if total else 0.0
        table.add_row(str(code), label, str(count), f"{pct:5.1f}%")

    console.print(table)

    ok_count: int = counts.get(rules.FLAG_OK, 0)
    flagged: int = total - ok_count

    if flagged == 0:
        console.print(
            "[success]All samples are currently flagged OK by the configured "
            "rules.[/success]"
        )
    else:
        console.print(
            f"[warning]{flagged} of {total} samples have at least one "
            "non-zero flag. Review before using in downstream analysis.[/warning]"
        )


def main() -> None:
    """
    Run the Hydro QC command-line interface.

    This function orchestrates:

    * Argument parsing.
    * Configuration loading.
    * Time series reading.
    * QC rule application.
    * Flag summarisation.
    * Writing of outputs and optional terminal chart preview.

    It is intended to be used as the entry point for the ``hydro-qc``
    console script.
    """
    parser = build_parser()
    args = parser.parse_args()

    _print_header(args.config)

    console.print("[info]Loading configuration...[/info]")
    cfg: QCConfig = load_config(args.config)

    console.print(
        f"[info]Reading time series from [bold]{cfg.data.input_csv}[/bold]..."
        "[/info]"
    )
    df = read_ts(cfg.data)
    value_col = cfg.data.value_column

    if value_col not in df.columns:
        console.print(
            f"[error]Value column '{value_col}' not found in data.[/error]"
        )
        raise SystemExit(1)

    _print_dataset_summary(df, value_col)
    _print_rule_config(cfg)

    flag_series_list: List[pd.Series] = []

    candidates: List[Tuple[str, bool]] = [
        ("Range check", cfg.range_check.enabled),
        ("Stuck sensor", cfg.stuck_sensor.enabled),
        ("Spike MAD", cfg.spike_mad.enabled),
        ("Step rate", cfg.step_rate.enabled),
    ]

    active_rule_names: List[str] = [
        name for name, enabled in candidates if enabled
    ]
    if not active_rule_names:
        console.print(
            "[warning]No QC rules are enabled in the config; "
            "all data will be flagged as OK.[/warning]"
        )

    console.print("\n[step]Applying QC rules...[/step]")
    if args.no_progress:
        rule_iter: Iterable[str] = active_rule_names
    else:
        rule_iter = tqdm(active_rule_names, desc="QC rules", unit="rule")

    for rule_name in rule_iter:
        if rule_name == "Range check":
            fs = rules.apply_range_check(
                df[value_col],
                cfg.range_check.min,
                cfg.range_check.max,
            )
        elif rule_name == "Stuck sensor":
            fs = rules.apply_stuck_sensor(
                df[value_col],
                cfg.stuck_sensor.window,
                cfg.stuck_sensor.tolerance,
            )
        elif rule_name == "Spike MAD":
            fs = rules.apply_spike_mad(
                df[value_col],
                cfg.spike_mad.window,
                cfg.spike_mad.threshold,
            )
        elif rule_name == "Step rate":
            fs = rules.apply_step_rate(
                df[value_col],
                cfg.step_rate.max_change_per_step,
            )
        else:
            continue

        flag_series_list.append(fs)

    if flag_series_list:
        combined_flags = rules.combine_flags(*flag_series_list)
    else:
        combined_flags = pd.Series(
            data=rules.FLAG_OK,
            index=df.index,
            dtype="int64",
        )

    df["qc_flag"] = combined_flags

    console.print("\n[step]Summarising QC flags...[/step]")
    _print_flag_summary(df)

    console.print("\n[step]Writing outputs to disk...[/step]")
    ensure_dir(cfg.output.flags_csv)
    ensure_dir(cfg.output.combined_csv)
    ensure_dir(os.path.join(cfg.output.charts_dir, "dummy.txt"))
    ensure_dir(cfg.output.report_path)

    df[["qc_flag"]].to_csv(cfg.output.flags_csv)
    df.to_csv(cfg.output.combined_csv)

    chart_path = plot_series_with_flags(
        df=df,
        value_column=value_col,
        flag_column="qc_flag",
        out_dir=cfg.output.charts_dir,
        station_name=cfg.output.station_name,
    )

    generate_summary(
        df=df,
        value_column=value_col,
        flag_column="qc_flag",
        out_cfg=cfg.output,
        chart_path=os.path.relpath(
            chart_path,
            os.path.dirname(cfg.output.report_path),
        ),
    )

    out_table = Table(title="Outputs", show_lines=True)
    out_table.add_column("Artifact", style="cyan", no_wrap=True)
    out_table.add_column("Path", style="white")

    out_table.add_row("Flags CSV", cfg.output.flags_csv)
    out_table.add_row("Combined CSV", cfg.output.combined_csv)
    out_table.add_row("Chart (PNG)", chart_path)
    out_table.add_row("Summary report", cfg.output.report_path)

    console.print(out_table)

    if not args.no_chart_preview:
        _preview_chart_terminal(df, value_col)

    console.print(
        Panel.fit(
            "[success]QC complete.[/success]\n"
            "Use the flag summary and chart to decide whether to clean, "
            "gap-fill, or discard suspect periods before further analysis.",
            title="Done",
            border_style="success",
        )
    )


if __name__ == "__main__":
    main()
