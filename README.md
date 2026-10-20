# Cloud Incident Analyzer

An offline Python CLI that turns **synthetic service telemetry** into a prioritized JSON incident report. It validates CSV input, detects threshold violations, and groups repeated anomalies by service, region, and host so isolated noisy samples do not become incidents.

This project demonstrates input validation, deterministic data processing, reliability diagnostics, and automated testing. It runs locally using the Python standard library; no AWS account, credentials, network connection, or third-party runtime packages are required.

## Features

- Validate timezone-aware timestamps, nonblank labels, and finite numeric metrics with CSV line numbers on errors.
- Detect high latency, packet loss, elevated error rates, and CPU saturation.
- Require a configurable number of consecutive anomalous observations to suppress single-sample noise.
- Separate incidents by `(service, region, host)` and close a run when a healthy sample arrives.
- Prioritize critical incidents, order each severity group chronologically, and attach signal-based diagnostic suggestions.
- Write a JSON report and print a concise CLI summary.

## Architecture and technologies

```text
Telemetry CSV
     |
     v
load_csv()  ->  validated Sample records, sorted by host and time
     |
     v
signals()   ->  threshold violations for each observation
     |
     v
analyze()   ->  consecutive runs, severity, suggested checks
     |
     v
JSON report + terminal summary
```

| Component | Responsibility |
| --- | --- |
| `cloudtriage/core.py` | Data classes, CSV validation, detection, and incident grouping |
| `cloudtriage/__main__.py` | `argparse` CLI and JSON file output |
| `sample_data/telemetry.csv` | Small synthetic input for a reproducible example |
| `sample_report.json` | Expected report for the included input |
| `tests/` | Standard-library `unittest` tests, including CLI regression checks |
| `pyproject.toml` | Python package metadata and optional installation |
| `.github/workflows/tests.yml` | Automated tests and installation checks |

**Stack:** Python 3.10+, `csv`, `datetime`, `dataclasses`, `json`, `argparse`, and `unittest`. The implementation loads and sorts the input in memory: processing takes `O(n log n)` time and `O(n)` space for `n` samples.

## Setup and installation

Clone the repository and run commands from its root:

```bash
git clone https://github.com/ZaidW77/cloud-incident-analyzer.git
cd cloud-incident-analyzer
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use `py -3 -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell. The examples below use the activated environment's `python`.

Running from the checkout needs no package installation. To import the package or run its CLI from another directory, optionally install it:

```bash
python -m pip install .
```

Installation downloads the `setuptools` build dependency if needed. The sample CSV and report live in the checkout; use their full paths when running elsewhere.

## Run the example

```bash
python -m cloudtriage --input sample_data/telemetry.csv --output report.json
```

Expected terminal output:

```text
Analyzed 11 samples; found 3 incidents (1 critical). Report: report.json
```

The generated report matches [sample_report.json](sample_report.json). Its first incident begins with these fields (excerpt):

```json
{
  "service": "orders",
  "region": "us-east-1",
  "host": "api-01",
  "start": "2026-10-01T09:01:00+00:00",
  "end": "2026-10-01T09:02:00+00:00",
  "severity": "critical",
  "sample_count": 2
}
```

Additional commands:

```bash
# Include isolated anomalous observations as incidents.
python -m cloudtriage --input sample_data/telemetry.csv --output reports/all.json --min-consecutive 1

# Show available arguments.
python -m cloudtriage --help
```

Output directories are created automatically. Invalid input or an invalid window produces an error and a nonzero exit code. Input and output must be different files. An existing report at the selected output path is overwritten.

## Input contract and detection rules

The CSV must contain these columns:

```text
timestamp,service,region,host,latency_ms,packet_loss_pct,error_rate_pct,cpu_pct
```

Timestamps use timezone-aware ISO 8601, such as `2026-10-01T09:00:00Z`. Service, region, and host must be nonblank. Latency must be finite and nonnegative; percentage metrics must be finite and in `[0, 100]`. Additional named columns are ignored. Missing required values or surplus row cells are rejected.

| Signal | Inclusive trigger |
| --- | --- |
| High latency | `latency_ms >= 250` |
| Packet loss | `packet_loss_pct >= 3` |
| High error rate | `error_rate_pct >= 5` |
| CPU saturation | `cpu_pct >= 90` |

By default, an incident needs **two adjacent anomalous samples** for the same host key. Different signals can contribute to the same run. A loss or error rate of at least 10% anywhere in the run makes it `critical`; all other emitted incidents are `warning`. Start and end are the first and last anomalous observation, including a run that remains open at end of input.

## Testing

Run the complete suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

Tests cover inclusive thresholds, severity, noise suppression, host isolation, incident splitting, ordering across timezone offsets, malformed CSV and nonfinite metrics, empty input, and the actual CLI. The CLI sample test compares the generated JSON against the checked-in report.

GitHub Actions is configured to run the suite, install the package, and check the installed CLI on Python 3.10, 3.12, and 3.14 for pushes and pull requests.

## Design decisions and limitations

- **Consecutive observations, not a time window:** missing samples do not close an incident; a healthy observation does. Region names are labels, with no AWS integration.
- **Explainable thresholds:** rules and suggested checks are easy to trace to code. They are illustrative values, not production SLOs or confirmed root causes.
- **Batch processing:** the full input is held in memory. There is no streaming ingestion, persistence, dashboard, alert delivery, or machine-learning model.
- **Interview discussion:** explain why sorting is needed, how a healthy sample splits a run, why repeated observations reduce noise, and what additional state would be needed for streaming detection.
