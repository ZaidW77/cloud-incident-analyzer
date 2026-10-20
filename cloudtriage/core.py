"""Normalize telemetry, flag reliability signals, and collapse repeated alerts.

Only the Python standard library is required. This is an offline incident-analysis
portfolio project, not a real-time monitoring platform.
"""
from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Sample:
    timestamp: datetime
    service: str
    region: str
    host: str
    latency_ms: float
    packet_loss_pct: float
    error_rate_pct: float
    cpu_pct: float


@dataclass(frozen=True)
class Incident:
    service: str
    region: str
    host: str
    start: str
    end: str
    severity: str
    sample_count: int
    signals: list[str]
    suggested_checks: list[str]


REQUIRED = {
    'timestamp', 'service', 'region', 'host', 'latency_ms',
    'packet_loss_pct', 'error_rate_pct', 'cpu_pct',
}


def load_csv(path: str | Path) -> list[Sample]:
    """Parse and validate an input CSV, rejecting malformed telemetry."""
    result: list[Sample] = []
    with Path(path).open(newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            missing = sorted(REQUIRED - set(reader.fieldnames or []))
            raise ValueError(f'Missing CSV columns: {", ".join(missing)}')
        for row in reader:
            try:
                if None in row:
                    raise ValueError('more fields than CSV header')
                stamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                if stamp.tzinfo is None:
                    raise ValueError('timestamp needs a timezone')
                metrics = [float(row[key]) for key in (
                    'latency_ms', 'packet_loss_pct', 'error_rate_pct', 'cpu_pct'
                )]
                if any(not math.isfinite(x) for x in metrics):
                    raise ValueError('metrics must be finite numbers')
                if any(x < 0 for x in metrics) or any(x > 100 for x in metrics[1:]):
                    raise ValueError('metrics outside valid ranges')
                labels = [row[key].strip() for key in ('service', 'region', 'host')]
                if any(not v for v in labels):
                    raise ValueError('blank service, region, or host')
                result.append(Sample(stamp, *labels, *metrics))
            except (TypeError, KeyError, ValueError, AttributeError) as exc:
                raise ValueError(f'Invalid sample at CSV line {reader.line_num}: {exc}') from exc
    return sorted(result, key=lambda sample: (
        sample.service, sample.region, sample.host, sample.timestamp
    ))


def signals(sample: Sample) -> list[str]:
    flags = []
    if sample.latency_ms >= 250:
        flags.append('high_latency')
    if sample.packet_loss_pct >= 3:
        flags.append('packet_loss')
    if sample.error_rate_pct >= 5:
        flags.append('high_error_rate')
    if sample.cpu_pct >= 90:
        flags.append('cpu_saturation')
    return flags


def _checks(flags: Iterable[str]) -> list[str]:
    actions = {
        'high_latency': 'Inspect request latency and upstream dependencies.',
        'packet_loss': 'Check interface errors, paths, and packet drops.',
        'high_error_rate': 'Inspect service logs, deploys, and dependency health.',
        'cpu_saturation': 'Inspect process CPU, saturation, and autoscaling.',
    }
    return [actions[flag] for flag in sorted(set(flags))]


def _severity(group: list[tuple[Sample, list[str]]]) -> str:
    if any(sample.packet_loss_pct >= 10 or sample.error_rate_pct >= 10
           for sample, _ in group):
        return 'critical'
    return 'warning'


def analyze(samples: Iterable[Sample], *, min_consecutive: int = 2) -> dict:
    """Consolidate adjacent anomalous samples per host.

    A healthy sample closes the active incident. At least two consecutive anomalous
    samples are required by default to suppress single-sample noise.
    """
    if min_consecutive < 1:
        raise ValueError('min_consecutive must be positive')
    sorted_samples = sorted(samples, key=lambda s: (
        s.service, s.region, s.host, s.timestamp
    ))
    events: list[Incident] = []
    active: list[tuple[Sample, list[str]]] = []
    last_key: tuple[str, str, str] | None = None

    def close() -> None:
        if len(active) < min_consecutive:
            return
        first, last = active[0][0], active[-1][0]
        all_flags = sorted({flag for _, found in active for flag in found})
        events.append(Incident(
            first.service, first.region, first.host,
            first.timestamp.isoformat(), last.timestamp.isoformat(),
            _severity(active), len(active), all_flags, _checks(all_flags),
        ))

    for sample in sorted_samples:
        key = (sample.service, sample.region, sample.host)
        if key != last_key:
            close()
            active = []
            last_key = key
        found = signals(sample)
        if found:
            active.append((sample, found))
        else:
            close()
            active = []
    close()
    events.sort(key=lambda event: (
        event.severity != 'critical', datetime.fromisoformat(event.start), event.service
    ))
    return {
        'samples_analyzed': len(sorted_samples),
        'incident_count': len(events),
        'critical_count': sum(event.severity == 'critical' for event in events),
        'incidents': [asdict(event) for event in events],
    }
