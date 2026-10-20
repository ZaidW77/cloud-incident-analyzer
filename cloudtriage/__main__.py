"""CLI entry point: python -m cloudtriage --input ... --output ..."""
import argparse
import csv
import json
from pathlib import Path

from .core import analyze, load_csv


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyze reliability telemetry CSV')
    parser.add_argument('--input', type=Path, required=True, help='Telemetry CSV file')
    parser.add_argument('--output', type=Path, required=True, help='Destination JSON report')
    parser.add_argument('--min-consecutive', type=int, default=2,
                        help='Minimum adjacent anomalous observations per incident (default: 2)')
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError('input and output must be different files')
        report = analyze(load_csv(args.input), min_consecutive=args.min_consecutive)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    print(f"Analyzed {report['samples_analyzed']} samples; "
          f"found {report['incident_count']} incidents "
          f"({report['critical_count']} critical). Report: {args.output}")


if __name__ == '__main__':
    main()
