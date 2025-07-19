import argparse
import os
import pandas as pd

from hydxc.config import load_config
from hydxc.io import read_ts, ensure_dir
from hydxc import rules
from hydxc.plotting import plot_series_with_flags
from hydxc.report import generate_summary

def main():
    parser = argparse.ArgumentParser(
        description="Hydro QC Toolkit – rainfall & level QC"
    )
    parser.add_argument(
        "-c", "--config",
        required=True,
        help="Path to YAML config file",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)

    df = read_ts(cfg.data)
    value_col = cfg.data.value_column

    flag_series_list = []

    if cfg.range_check.enabled:
        flag_series_list.append(
            rules.apply_range_check(df[value_col],
                                       cfg.range_check.min,
                                       cfg.range_check.max)
        )
    if cfg.stuck_sensor.enabled:
        flag_series_list.append(
            rules.apply_stuck_sensor(df[value_col],
                                        cfg.stuck_sensor.window,
                                        cfg.stuck_sensor.tolerance)
        )
    if cfg.spike_mad.enabled:
        flag_series_list.append(
            rules.apply_spike_mad(df[value_col],
                                     cfg.spike_mad.window,
                                     cfg.spike_mad.threshold)
        )
    if cfg.step_rate.enabled:
        flag_series_list.append(
            rules.apply_step_rate(df[value_col],
                                     cfg.step_rate.max_change_per_step)
        )

    if flag_series_list:
        combined_flags = rules.combine_flags(*flag_series_list)
    else:
        combined_flags = pd.Series(rules.FLAG_OK,
                                   index=df.index,
                                   dtype="int64")

    df["qc_flag"] = combined_flags

    # Outputs
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
        chart_path=os.path.relpath(chart_path,
                                   os.path.dirname(cfg.output.report_path)),
    )

    print("QC complete.")
    print(f"- Flags CSV: {cfg.output.flags_csv}")
    print(f"- Combined CSV: {cfg.output.combined_csv}")
    print(f"- Chart: {chart_path}")
    print(f"- Report: {cfg.output.report_path}")
