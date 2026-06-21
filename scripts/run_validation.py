"""Run temporal validation for the grouped-median baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from house_valuation.data.loaders import load_csv_dataset
from house_valuation.evaluation.validation import run_baseline_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to processed modelling CSV.")
    parser.add_argument("--holdout-months", type=int, default=12)
    parser.add_argument("--min-group-support", type=int, default=3)
    args = parser.parse_args()

    rows = load_csv_dataset(args.dataset)
    result = run_baseline_validation(
        rows,
        holdout_months=args.holdout_months,
        min_group_support=args.min_group_support,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

