"""Transparent multi-property assessment for PPR Checkpoint 4.

Rules are loaded from reviewed CSV metadata. Regex matching is vectorised, while
the distinct-block rule remains named structural logic. The resulting evidence
tiers are deterministic labels rather than statistical probabilities.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa


SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}
ACTION_RANK = {"none": 0, "review_only": 1, "auto_exclude": 2}
VALID_MATCHERS = {"regex", "multiple_named_blocks"}
MULTI_PROPERTY_FIELDS = [
    pa.field("is_possible_multi_property_sale", pa.bool_(), nullable=False),
    pa.field("multi_property_rule_ids", pa.string(), nullable=False),
    pa.field("multi_property_reason", pa.string(), nullable=False),
    pa.field("multi_property_max_severity", pa.string(), nullable=False),
    pa.field("multi_property_action", pa.string(), nullable=False),
    pa.field("single_dwelling_confidence", pa.string(), nullable=False),
]


class MultiPropertyConfigError(ValueError):
    """Raised when multi-property rule configuration is invalid."""


@dataclass(frozen=True)
class MultiPropertyRule:
    """One configured multi-property rule.

    Attributes:
        rule_id: Stable audit identifier.
        description: Plain-language rule description.
        matcher: Registered matching implementation.
        pattern: Compiled regular expression.
        severity: Evidence tier.
        action: Cleaning action.
        rationale: Reason the rule exists.
        false_positive_risk: Known limitation.
    """

    rule_id: str
    description: str
    matcher: str
    pattern: re.Pattern[str]
    severity: str
    action: str
    rationale: str
    false_positive_risk: str


def load_multi_property_rules(path: str | Path) -> list[MultiPropertyRule]:
    """Load and validate deterministic multi-property rules.

    Args:
        path: CSV rule configuration path.

    Returns:
        Rules sorted by stable rule ID.

    Raises:
        MultiPropertyConfigError: If metadata, enums, IDs, or regexes are invalid.
    """

    required = {
        "rule_id", "description", "matcher", "pattern", "severity", "action",
        "rationale", "false_positive_risk",
    }
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise MultiPropertyConfigError(f"Multi-property config must contain {sorted(required)}")
        raw_rows = list(reader)
    if not raw_rows:
        raise MultiPropertyConfigError("Multi-property config contains no rules.")
    ids = [row["rule_id"].strip() for row in raw_rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise MultiPropertyConfigError("Multi-property rule IDs must be non-empty and unique.")
    rules: list[MultiPropertyRule] = []
    for row in raw_rows:
        matcher = row["matcher"].strip()
        severity = row["severity"].strip()
        action = row["action"].strip()
        if matcher not in VALID_MATCHERS:
            raise MultiPropertyConfigError(f"Unknown matcher for {row['rule_id']}: {matcher}")
        if severity not in SEVERITY_RANK or severity == "none":
            raise MultiPropertyConfigError(f"Invalid severity for {row['rule_id']}: {severity}")
        if action not in {"auto_exclude", "review_only"}:
            raise MultiPropertyConfigError(f"Invalid action for {row['rule_id']}: {action}")
        try:
            compiled = re.compile(row["pattern"], flags=re.IGNORECASE)
        except re.error as exc:
            raise MultiPropertyConfigError(f"Invalid regex for {row['rule_id']}: {exc}") from exc
        rules.append(MultiPropertyRule(
            rule_id=row["rule_id"].strip(), description=row["description"].strip(),
            matcher=matcher, pattern=compiled, severity=severity, action=action,
            rationale=row["rationale"].strip(),
            false_positive_risk=row["false_positive_risk"].strip(),
        ))
    return sorted(rules, key=lambda rule: rule.rule_id)


def assess_multi_property_frame(
    frame: pd.DataFrame,
    rules: list[MultiPropertyRule],
    *,
    address_column: str = "address_normalized",
) -> pd.DataFrame:
    """Append deterministic multi-property evidence to a copy of a frame.

    Args:
        frame: Checkpoint 3 records.
        rules: Validated rule definitions.
        address_column: Normalised address field to assess.

    Returns:
        Row-preserving copy with multi-property assessment fields.

    Raises:
        KeyError: If the address field is missing.
    """

    if address_column not in frame:
        raise KeyError(f"Missing multi-property address column: {address_column}")
    output = frame.copy()
    text = output[address_column].fillna("").astype(str)
    ids = pd.Series("", index=output.index, dtype="string")
    reasons = pd.Series("", index=output.index, dtype="string")
    severity = pd.Series("none", index=output.index, dtype="string")
    action = pd.Series("none", index=output.index, dtype="string")
    for rule in rules:
        mask = _rule_mask(text, rule)
        ids.loc[mask] = _append_pipe(ids.loc[mask], rule.rule_id)
        reasons.loc[mask] = _append_pipe(reasons.loc[mask], rule.description)
        severity.loc[mask & severity.map(SEVERITY_RANK).lt(SEVERITY_RANK[rule.severity])] = rule.severity
        action.loc[mask & action.map(ACTION_RANK).lt(ACTION_RANK[rule.action])] = rule.action
    output["is_possible_multi_property_sale"] = ids.ne("")
    output["multi_property_rule_ids"] = ids
    output["multi_property_reason"] = reasons
    output["multi_property_max_severity"] = severity
    output["multi_property_action"] = action
    output["single_dwelling_confidence"] = action.map(
        {"none": "high", "review_only": "medium", "auto_exclude": "low"}
    ).astype("string")
    return output


def rule_match_counts(frame: pd.DataFrame, rules: list[MultiPropertyRule]) -> dict[str, int]:
    """Count rule IDs in an assessed frame.

    Args:
        frame: Assessed records.
        rules: Active rules.

    Returns:
        Mapping from rule ID to participating row count.
    """

    values = frame["multi_property_rule_ids"].fillna("")
    return {rule.rule_id: int(values.str.contains(fr"(?:^|\|){re.escape(rule.rule_id)}(?:\||$)").sum()) for rule in rules}


def _rule_mask(text: pd.Series, rule: MultiPropertyRule) -> pd.Series:
    """Return the vectorised match mask for one configured rule."""

    if rule.matcher == "regex":
        return text.str.contains(rule.pattern, na=False)
    matches = text.str.findall(rule.pattern)
    return matches.map(lambda values: len(set(values)) >= 2)


def _append_pipe(values: pd.Series, token: str) -> pd.Series:
    """Append one stable token to pipe-delimited values."""

    return values.where(values.eq(""), values + "|") + token
