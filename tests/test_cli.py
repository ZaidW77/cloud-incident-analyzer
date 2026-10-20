"""Exercise the public module entry point using temporary output files."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, '-m', 'cloudtriage', *map(str, args)],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )

    def test_sample_matches_checked_in_report(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'reports' / 'report.json'
            result = self.run_cli('--input', 'sample_data/telemetry.csv', '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Analyzed 11 samples; found 3 incidents (1 critical)', result.stdout)
            expected = json.loads((ROOT / 'sample_report.json').read_text(encoding='utf-8'))
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), expected)

    def test_missing_input_has_readable_error(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'report.json'
            result = self.run_cli('--input', Path(temp) / 'missing.csv', '--output', output)
            self.assertEqual(result.returncode, 2)
            self.assertIn('error:', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse(output.exists())

    def test_invalid_window_does_not_write_report(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'report.json'
            result = self.run_cli('--input', 'sample_data/telemetry.csv',
                                  '--output', output, '--min-consecutive', '0')
            self.assertEqual(result.returncode, 2)
            self.assertIn('min_consecutive must be positive', result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_overwriting_input(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'telemetry.csv'
            original = (ROOT / 'sample_data/telemetry.csv').read_bytes()
            path.write_bytes(original)
            result = self.run_cli('--input', path, '--output', path)
            self.assertEqual(result.returncode, 2)
            self.assertIn('different files', result.stderr)
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
