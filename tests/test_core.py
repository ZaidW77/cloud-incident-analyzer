import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cloudtriage.core import Sample, analyze, load_csv, signals


START = datetime(2026, 10, 1, tzinfo=timezone.utc)


def sample(minute=0, host='app-01', loss=0, errors=0, latency=40, cpu=20):
    return Sample(START + timedelta(minutes=minute), 'api', 'us-east-1', host,
                  latency, loss, errors, cpu)


class AnalyzeTests(unittest.TestCase):
    def test_thresholds_are_inclusive(self):
        self.assertEqual(signals(sample(loss=3, errors=5, latency=250, cpu=90)),
                         ['high_latency', 'packet_loss', 'high_error_rate', 'cpu_saturation'])

    def test_suppresses_single_anomalous_sample(self):
        self.assertEqual(analyze([sample(loss=4)])['incident_count'], 0)

    def test_consecutive_samples_form_one_incident(self):
        report = analyze([sample(1, loss=4), sample(0, loss=12)])
        self.assertEqual(report['incident_count'], 1)
        self.assertEqual(report['critical_count'], 1)
        self.assertEqual(report['incidents'][0]['sample_count'], 2)

    def test_healthy_samples_split_incidents(self):
        report = analyze([sample(0, loss=4), sample(1, loss=4), sample(2),
                          sample(3, errors=5), sample(4, errors=5)])
        self.assertEqual(report['incident_count'], 2)

    def test_hosts_isolated(self):
        report = analyze([sample(0, loss=4), sample(1, loss=4),
                          sample(0, 'app-02', errors=6), sample(1, 'app-02', errors=6)])
        self.assertEqual(report['incident_count'], 2)

    def test_empty_samples(self):
        self.assertEqual(analyze([])['incidents'], [])

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            analyze([], min_consecutive=0)

    def test_csv_validation_and_sort(self):
        rows = [
            {'timestamp': (START + timedelta(minutes=i)).isoformat(),
             'service': 'api', 'region': 'us-east-1', 'host': 'app-01',
             'latency_ms': '45', 'packet_loss_pct': '0', 'error_rate_pct': '0',
             'cpu_pct': '25'} for i in (2, 0, 1)
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'telemetry.csv'
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader(); writer.writerows(rows)
            loaded = load_csv(path)
        self.assertEqual(loaded[0].timestamp, START)

    def test_rejects_out_of_range_percentages(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.csv'
            path.write_text('timestamp,service,region,host,latency_ms,packet_loss_pct,error_rate_pct,cpu_pct\n'
                            '2026-10-01T12:00:00Z,api,us-east-1,app-01,25,110,1,5\n')
            with self.assertRaisesRegex(ValueError, 'line 2'):
                load_csv(path)


if __name__ == '__main__':
    unittest.main()
