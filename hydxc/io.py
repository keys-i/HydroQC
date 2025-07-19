import os
import pandas as pd

from hydxc.config import DataConfig


def read_ts(cfg: DataConfig) -> pd.DataFrame:
    df = pd.read_csv(cfg.input_csv)

    # Parse datetime
    if cfg.datetime_format:
        df[cfg.time_column] = pd.to_datetime(
            df[cfg.time_column], format=cfg.datetime_format
        )
    else:
        df[cfg.time_column] = pd.to_datetime(df[cfg.time_column])

    df = df.set_index(cfg.time_column).sort_index()
    return df


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
