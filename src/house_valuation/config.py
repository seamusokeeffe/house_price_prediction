"""Project configuration and locked V1 constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_HOUSE_TYPES = {
    "House",
    "Detached House",
    "Semi-Detached House",
    "Terraced House",
    "End of Terrace House",
}

UNKNOWN_PROPERTY_TYPE = "unknown"

REQUIRED_TRAINING_COLUMNS = {
    "transaction_date",
    "sale_price_eur",
    "canonical_area",
    "property_type",
}


@dataclass(frozen=True)
class ProjectConfig:
    """Runtime paths for local scripts."""

    dataset_path: Path
    artifacts_dir: Path = Path("artifacts")
    validation_holdout_months: int = 12
    min_group_support: int = 3

    @classmethod
    def from_paths(
        cls,
        dataset_path: str | Path,
        artifacts_dir: str | Path = "artifacts",
        validation_holdout_months: int = 12,
        min_group_support: int = 3,
    ) -> "ProjectConfig":
        return cls(
            dataset_path=Path(dataset_path),
            artifacts_dir=Path(artifacts_dir),
            validation_holdout_months=validation_holdout_months,
            min_group_support=min_group_support,
        )

