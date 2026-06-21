"""Train the grouped-median baseline and save a local artifact."""

from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from house_valuation.config import ProjectConfig
from house_valuation.data.filters import filter_training_rows
from house_valuation.data.loaders import load_csv_dataset
from house_valuation.models.baseline import GroupedMedianBaseline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to processed modelling CSV.")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Directory for model artifact output.")
    parser.add_argument("--min-group-support", type=int, default=3)
    args = parser.parse_args()

    config = ProjectConfig.from_paths(args.dataset, args.artifacts_dir, min_group_support=args.min_group_support)
    rows = filter_training_rows(load_csv_dataset(config.dataset_path))
    model = GroupedMedianBaseline(min_group_support=config.min_group_support).fit(rows)

    config.artifacts_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.artifacts_dir / "grouped_median_baseline.pkl"
    with output_path.open("wb") as handle:
        pickle.dump(model, handle)

    print(f"Saved baseline model to {output_path}")
    print(f"Training rows: {len(rows)}")


if __name__ == "__main__":
    main()

