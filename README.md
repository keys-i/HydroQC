# Hydro QC Toolkit

Hydro QC Toolkit is a small command-line tool for running quality control checks on hydrological time series such as water level and rainfall.

The goal is to:

- Read CSV time series (rainfall and level)
- Apply a set of practical QC rules:
  - Range checks
  - Stuck sensor detection
  - Spike detection using Median Absolute Deviation (MAD)
  - Step rate checks
- Write out:
  - QC flags as a CSV
  - A combined CSV with original data and flags
  - Quick-look charts for operator review
  - A one-page summary that can be pasted into reports

This repository is at a very early stage. Interfaces and configuration details are still being worked out.

## Status

Early planning and scaffolding.

What exists now:

- Basic Python package layout
- Initial QC rule ideas sketched out
- `LICENSE` file added to the repository

What will be added next:

- YAML-based configuration format
- CSV I/O and QC rule implementations (pandas / NumPy)
- Simple CLI (`hydro-qc`) for running checks from the command line
- Basic matplotlib plots
- One-page Markdown/text summary

As the project stabilises, this README will be updated with concrete examples and full usage instructions.

## Planned structure (subject to change)

```text
hydqc/
  cli.py          # CLI entry point
  config.py       # YAML config loading
  io.py           # CSV I/O
  qc_rules.py     # QC rule implementations
  plotting.py     # Quick charts
  report.py       # One-page summary
examples/
  config_example.yaml
  sample_data.csv
tests/
  test_qc_rules.py
```

This structure is a working draft and may change as the project evolves.

## Getting started (draft)

This section will document:

* Python version and basic dependencies
* How to set up a virtual environment
* How to install the package in editable mode
* How to run the CLI against an example configuration

For now, this is just a placeholder while the code is still being written.

## License

This project is licensed under the terms described in the `LICENSE` file in this repository.

