from datetime import datetime
import pandas as pd

from hydxc.config import OutputConfig

FLAG_LABELS = {
    0: "OK",
    1: "Range",
    2: "Stuck sensor",
    3: "Spike (MAD)",
    4: "Step rate",
}

def generate_summary(
    df: pd.DataFrame,
    value_column: str,
    flag_column: str,
    out_cfg: OutputConfig,
    chart_path: str,
):
    total = len(df)
    counts = df[flag_column].value_counts().to_dict()

    lines = []
    lines.append(f"# QC Summary – {out_cfg.station_name}")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## Dataset")
    lines.append(f"- Samples: {total}")
    lines.append(f"- Start: {df.index.min().isoformat()}")
    lines.append(f"- End:   {df.index.max().isoformat()}")
    lines.append("")

    lines.append("## Flag statistics")
    for code, label in FLAG_LABELS.items():
        n = counts.get(code, 0)
        pct = 100 * n / total if total > 0 else 0
        lines.append(f"- {label}: {n} ({pct:.1f}%)")

    lines.append("")
    lines.append("## Quick view")
    lines.append(f"![QC chart]({chart_path})")
    lines.append("")
    lines.append("## Notes for operator")
    lines.append("- Review flagged points before using data in reports.")
    lines.append("- Range and spike flags may indicate real events or sensor faults.")
    lines.append("- Stuck sensor flags usually indicate a frozen sensor or communication issue.")
    lines.append("- Step-rate flags indicate abrupt changes that may need confirmation.")

    text = "\n".join(lines)

    with open(out_cfg.report_path, "w") as f:
        f.write(text)
