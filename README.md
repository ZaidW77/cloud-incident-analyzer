# Cloud Incident Analyzer

A small, runnable reliability engineering project for analyzing **synthetic** cloud-service telemetry. It demonstrates input validation, threshold-based anomaly detection, incident grouping, severity prioritization, actionable diagnostics, JSON reporting, CLI usage, and automated tests. It does **not** connect to AWS or claim production traffic.

## Quick start

Requires Python 3.10+ and no third-party packages.

```bash
python -m cloudtriage --input sample_data/telemetry.csv --output report.json
python -m unittest discover -s tests -v
```

Expected sample output: `Analyzed 11 samples; found 3 incidents (1 critical)`.

## Input contract

CSV columns: `timestamp` (timezone-aware ISO 8601), `service`, `region`, `host`, `latency_ms`, `packet_loss_pct`, `error_rate_pct`, and `cpu_pct`. Percentages must be 0–100, and latency cannot be negative. Malformed records fail with a line number.

## Detection design

| Signal | Trigger |
| --- | --- |
| high latency | ≥ 250 ms |
| packet loss | ≥ 3% |
| service error rate | ≥ 5% |
| CPU saturation | ≥ 90% |

By default, a host needs **two consecutive anomalous samples** before an incident is emitted. A healthy sample closes the incident. Incidents are separated by service, AWS-style region label, and host. A ≥10% loss or ≥10% error rate makes an incident critical. Diagnostic suggestions are derived from the observed signals.

## Notes and limitations

- Data is deliberately synthetic and threshold values are illustrative, not production SLOs.
- The incident algorithm consolidates consecutive *observations*, not time-bounded events. Missing samples do not automatically close an incident.
- This is an offline analysis CLI; for production use, consider streaming ingestion, persistence, alert routing, and richer baselines.

## Tests / CI

Automated tests cover severity, boundary thresholds, noisy single samples, incident splitting, multi-host isolation, ordering, malformed CSV and empty input. GitHub Actions runs the tests on every push and pull request.
