from dataclasses import dataclass
from typing import Optional
import yaml

@dataclass
class RangeConfig:
    enabled: bool
    min: float
    max: float

@dataclass
class StuckConfig:
    enabled: bool
    window: int
    tolerance: float

@dataclass
class SpikeMadConfig:
    enabled: bool
    window: int
    threshold: float

@dataclass
class StepConfig:
    enabled: bool
    max_change_per_step: float

@dataclass
class DataConfig:
    input_csv: str
    time_column: str
    value_column: str
    rainfall_column: Optional[str]
    datetime_format: Optional[str]
    timezone: Optional[str]

@dataclass
class OutputConfig:
    flags_csv: str
    combined_csv: str
    charts_dir: str
    report_path: str
    station_name: str

@dataclass
class QCConfig:
    data: DataConfig
    range_check: RangeConfig
    stuck_sensor: StuckConfig
    spike_mad: SpikeMadConfig
    step_rate: StepConfig
    output: OutputConfig

def load_config(path: str) -> QCConfig:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    data_section = raw["data"]
    qc_section = raw["qc"]
    out_section = raw["output"]

    return QCConfig(
        data=DataConfig(
            input_csv=data_section["input_csv"],
            time_column=data_section["time_column"],
            value_column=data_section["value_column"],
            rainfall_column=data_section.get("rainfall_column"),
            datetime_format=data_section.get("datetime_format"),
            timezone=data_section.get("timezone"),
        ),
        range_check=RangeConfig(**qc_section["range_check"]),
        stuck_sensor=StuckConfig(**qc_section["stuck_sensor"]),
        spike_mad=SpikeMadConfig(**qc_section["spike_mad"]),
        step_rate=StepConfig(**qc_section["step_rate"]),
        output=OutputConfig(
            **out_section
        ),
    )
