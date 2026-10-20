"""CLI entry point: python -m cloudtriage --input ... --output ..."""
import argparse
import json
from pathlib import Path

from .core import analyze, load_csv


def main() -> None:
    parser = argparse.ArgumentParser(description='Analyze reliability telemetry CSV')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--min-consecutive', type=int, default=2)
    args = parser.parse_args()
    report = analyze(load_csv(args.input), min_consecutive=args.min_consecutive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Analyzed {report['samples_analyzed']} samples; "
          f"found {report['incident_count']} incidents "
          f"({report['critical_count']} critical). Report: {args.output}")


if __name__ == '__main__':
    main()
