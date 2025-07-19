import os
import matplotlib.pyplot as plt
import pandas as pd

from hydxc.io import ensure_dir


def plot_series_with_flags(
    df: pd.DataFrame,
    value_column: str,
    flag_column: str,
    out_dir: str,
    station_name: str,
):
    ensure_dir(os.path.join(out_dir, "dummy.txt"))  # ensure dir exists

    fig, ax = plt.subplots(figsize=(10, 4))
    df[value_column].plot(ax=ax, label=value_column)

    # Overlay flagged points
    flagged = df[df[flag_column] != 0]
    if not flagged.empty:
        ax.scatter(
            flagged.index,
            flagged[value_column],
            marker="x",
            label="Flagged",
        )

    ax.set_title(f"{station_name} - {value_column} with QC flags")
    ax.set_xlabel("Time")
    ax.set_ylabel(value_column)
    ax.legend()
    fig.tight_layout()

    out_path = os.path.join(out_dir, f"{value_column}_qc.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
