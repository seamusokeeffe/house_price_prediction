"""Controlled canonical-area mapping for PPR Checkpoint 3.

The mapper uses reviewed aliases, optional manual overrides, Dublin-context
safeguards, and deterministic candidate resolution. It does not perform fuzzy
matching, geocoding, property-scope classification, or training exclusion.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from house_valuation.data.address_normalization import match_text, normalize_address_frame


INFERENCE_AREAS = [
    "Sandymount",
    "Ballsbridge",
    "Ranelagh",
    "Rathmines",
    "Rathgar",
    "Terenure",
    "Donnybrook",
    "Milltown",
    "Dartry",
    "Clonskeagh",
    "Windy Arbour",
    "Churchtown",
    "Dundrum",
    "Goatstown",
    "Foxrock",
    "Seapoint",
    "Blackrock",
    "Booterstown",
    "Merrion",
    "Mount Merrion",
    "Kilmacud",
    "Stillorgan",
    "Ardilea",
    "Monkstown",
]

TRAINING_ONLY_AREAS = [
    "Harolds Cross",
    "Kimmage",
    "Templeogue",
    "Rathfarnham",
    "Knocklyon",
    "Butterfield",
    "Edmondstown",
    "Ballyboden",
    "Scholarstown",
    "Ballinteer",
    "Balally",
    "Sandyford",
    "Kilgobbin",
    "Carrickmines",
    "Kilternan",
    "Deansgrange",
    "Cabinteely",
    "Loughlinstown",
    "Shankill",
    "Ballybrack",
    "Killiney",
    "Kilbogget",
    "Glenageary",
    "Thomastown",
    "Dalkey",
    "Woodpark",
    "Sandycove",
    "Dún Laoghaire",
]

LOCKED_SCOPE_BY_AREA = {area: "inference" for area in INFERENCE_AREAS} | {
    area: "training_only" for area in TRAINING_ONLY_AREAS
}

GEOGRAPHY_FIELDS = [
    pa.field("address_normalized", pa.string(), nullable=True),
    pa.field("address_match_text", pa.string(), nullable=True),
    pa.field("address_normalization_status", pa.string(), nullable=False),
    pa.field("address_quality_flags", pa.string(), nullable=False),
    pa.field("canonical_area", pa.string(), nullable=True),
    pa.field("geo_scope", pa.string(), nullable=False),
    pa.field("geography_match_status", pa.string(), nullable=False),
    pa.field("geography_match_method", pa.string(), nullable=False),
    pa.field("geography_match_alias", pa.string(), nullable=True),
    pa.field("geography_match_priority", pa.int64(), nullable=True),
    pa.field("geography_candidate_areas", pa.string(), nullable=False),
    pa.field("geography_quality_flags", pa.string(), nullable=False),
    pa.field("matched_aliases", pa.string(), nullable=False),
    pa.field("match_methods", pa.string(), nullable=False),
    pa.field("match_priorities", pa.string(), nullable=False),
]

POSTAL_DISTRICT_ONLY = re.compile(r"^(?:DUBLIN\s+\d{1,2}[A-Z]?|COUNTY\s+DUBLIN|DUBLIN)$")
BROAD_DUBLIN_REFERENCES = {
    "DUBLIN",
    "DUBLIN 4",
    "DUBLIN 6",
    "DUBLIN 6W",
    "DUBLIN 14",
    "DUBLIN 16",
    "SOUTH DUBLIN",
    "DUN LAOGHAIRE RATHDOWN",
    "DÚN LAOGHAIRE RATHDOWN",
}
NON_UNIQUE_AREAS = {"Blackrock", "Milltown", "Churchtown", "Monkstown", "Shankill"}
MATCH_TYPES = {"exact_address", "controlled_phrase", "token_phrase"}
SCOPES = {"inference", "training_only"}


class GeographyConfigError(ValueError):
    """Raised for invalid canonical-area or override configuration."""


class Checkpoint3PhysicalSchemaError(ValueError):
    """Raised when the checkpoint 3 Parquet output is not valid."""


@dataclass(frozen=True)
class CanonicalAlias:
    """One reviewed alias row from the canonical-area configuration.

    Attributes:
        canonical_area: Locked canonical project area.
        alias: Reviewed text alias from configuration.
        scope: Geography scope for the canonical area.
        match_type: Controlled matching mode for this alias.
        match_priority: Explicit deterministic priority.
        notes: Review notes from configuration.
        alias_match_text: Normalised comparison form of `alias`.
        phrase_pattern: Compiled token-boundary pattern for phrase matching.
    """

    canonical_area: str
    alias: str
    scope: str
    match_type: str
    match_priority: int
    notes: str
    alias_match_text: str
    phrase_pattern: re.Pattern[str]


@dataclass(frozen=True)
class GeographyMatch:
    """One candidate geography match before final resolution.

    Attributes:
        canonical_area: Candidate canonical area.
        scope: Candidate geography scope.
        method: Match method that produced the candidate.
        alias: Alias text that matched.
        priority: Explicit alias priority.
    """

    canonical_area: str
    scope: str
    method: str
    alias: str
    priority: int


@dataclass(frozen=True)
class GeographyResult:
    """Final geography mapping result for one record.

    Attributes mirror the documented Checkpoint 3 geography output fields.
    """

    canonical_area: str | pd.NA
    geo_scope: str
    geography_match_status: str
    geography_match_method: str
    geography_match_alias: str | pd.NA
    geography_match_priority: int | pd.NA
    geography_candidate_areas: str
    geography_quality_flags: str
    matched_aliases: str
    match_methods: str
    match_priorities: str


def load_canonical_aliases(path: str | Path) -> list[CanonicalAlias]:
    """Load and validate canonical-area aliases.

    Args:
        path: CSV path containing canonical areas and aliases.

    Returns:
        Deterministically sorted alias records.

    Raises:
        GeographyConfigError: If required columns are missing, an area is not
            locked, a scope is inconsistent, or locked area coverage is
            incomplete.
    """

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"canonical_area", "alias", "scope", "match_type", "match_priority", "notes"}
    if not rows:
        raise GeographyConfigError("Canonical-area configuration is empty.")
    missing = required - set(rows[0])
    if missing:
        raise GeographyConfigError(f"Canonical-area configuration missing columns: {', '.join(sorted(missing))}")

    aliases: list[CanonicalAlias] = []
    areas_seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        area = row["canonical_area"].strip()
        alias = row["alias"].strip()
        scope = row["scope"].strip()
        match_type = row["match_type"].strip()
        if area not in LOCKED_SCOPE_BY_AREA:
            raise GeographyConfigError(f"Unknown canonical area on row {index}: {area}")
        if scope != LOCKED_SCOPE_BY_AREA[area] or scope not in SCOPES:
            raise GeographyConfigError(f"Scope mismatch for {area} on row {index}: {scope}")
        if match_type not in MATCH_TYPES:
            raise GeographyConfigError(f"Invalid match_type on row {index}: {match_type}")
        if not alias:
            raise GeographyConfigError(f"Missing alias on row {index}")
        try:
            priority = int(row["match_priority"])
        except ValueError as exc:
            raise GeographyConfigError(f"Invalid match_priority on row {index}: {row['match_priority']}") from exc
        alias_match_text = match_text(alias)
        aliases.append(
            CanonicalAlias(
                canonical_area=area,
                alias=alias,
                scope=scope,
                match_type=match_type,
                match_priority=priority,
                notes=row.get("notes", "").strip(),
                alias_match_text=alias_match_text,
                phrase_pattern=_phrase_pattern(alias_match_text),
            )
        )
        areas_seen.add(area)

    expected = set(LOCKED_SCOPE_BY_AREA)
    if areas_seen != expected:
        missing_areas = sorted(expected - areas_seen)
        extra_areas = sorted(areas_seen - expected)
        raise GeographyConfigError(
            f"Canonical-area configuration does not match locked geography. "
            f"Missing={missing_areas}; extra={extra_areas}"
        )
    return sorted(aliases, key=lambda alias: (alias.match_priority, alias.canonical_area, alias.alias_match_text))


def load_manual_overrides(path: str | Path, aliases: list[CanonicalAlias]) -> dict[str, GeographyMatch]:
    """Load reviewed record-level geography overrides.

    Args:
        path: CSV path containing overrides. A missing file means no overrides.
        aliases: Loaded aliases used to validate override areas and scopes.

    Returns:
        Mapping from `record_id` to override match.

    Raises:
        GeographyConfigError: If override columns are missing, an area is
            unknown, a scope mismatches, or a record has conflicting overrides.
    """

    override_path = Path(path)
    if not override_path.exists():
        return {}
    with override_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return {}
    required = {"record_id", "canonical_area", "geo_scope", "override_reason", "reviewed_by", "review_date", "notes"}
    missing = required - set(rows[0])
    if missing:
        raise GeographyConfigError(f"Override configuration missing columns: {', '.join(sorted(missing))}")

    known_area_scope = {alias.canonical_area: alias.scope for alias in aliases}
    overrides: dict[str, GeographyMatch] = {}
    raw_by_record: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows, start=2):
        record_id = row["record_id"].strip()
        if not record_id:
            continue
        area = row["canonical_area"].strip()
        scope = row["geo_scope"].strip()
        if area not in known_area_scope:
            raise GeographyConfigError(f"Override references unknown canonical area on row {index}: {area}")
        if scope != known_area_scope[area]:
            raise GeographyConfigError(f"Override scope mismatch for {area} on row {index}: {scope}")
        previous = raw_by_record.get(record_id)
        current_key = {"canonical_area": area, "geo_scope": scope}
        if previous is not None and previous != current_key:
            raise GeographyConfigError(f"Conflicting manual overrides for record_id {record_id}")
        raw_by_record[record_id] = current_key
        overrides[record_id] = GeographyMatch(area, scope, "manual_override", "manual_override", 0)
    return overrides


class GeographyMapper:
    """Deterministic mapper from normalised address rows to canonical areas."""

    def __init__(self, aliases: list[CanonicalAlias], overrides: dict[str, GeographyMatch] | None = None):
        """Initialise the mapper.

        Args:
            aliases: Reviewed alias rules.
            overrides: Optional record-level manual overrides.
        """

        self.aliases = aliases
        self.overrides = overrides or {}

    def map_record(self, row: pd.Series | dict[str, Any]) -> GeographyResult:
        """Map one normalised row to a canonical area or audit status.

        Args:
            row: Row containing `record_id`, address-normalisation fields, and
                Dublin-context fields such as `county_raw`.

        Returns:
            Resolved match, ambiguity, invalid-address, or unmatched result.
        """

        record_id = str(row.get("record_id", ""))
        normalized_status = str(row.get("address_normalization_status", ""))
        address_match_text = "" if pd.isna(row.get("address_match_text")) else str(row.get("address_match_text"))
        county_text = match_text(row.get("county_raw", ""))

        if record_id in self.overrides:
            return self._from_override(self.overrides[record_id])
        if normalized_status in {"missing", "too_short"} or not address_match_text:
            return GeographyResult(pd.NA, "unknown", "invalid_address", "none", pd.NA, pd.NA, "", "invalid_or_missing_address", "", "", "")

        matches = self._candidate_matches(address_match_text)
        quality_flags = self._quality_flags(address_match_text, county_text, matches)

        if not _has_dublin_context(address_match_text, county_text):
            if matches:
                quality_flags.append("canonical_alias_outside_expected_dublin_context")
            status = "unmatched"
            scope = "out_of_scope" if county_text and county_text != "DUBLIN" else "unknown"
            return GeographyResult(pd.NA, scope, status, "none", pd.NA, pd.NA, "", "|".join(sorted(set(quality_flags))), "", "", "")

        matches = [match for match in matches if not self._blocked_by_context(match, address_match_text)]
        if not matches:
            status = "unmatched"
            scope = "unknown" if _maybe_dublin(address_match_text, county_text) else "out_of_scope"
            return GeographyResult(pd.NA, scope, status, "none", pd.NA, pd.NA, "", "|".join(sorted(set(quality_flags))), "", "", "")

        unique_by_area = self._best_by_area(matches)
        if len(unique_by_area) == 1:
            match = unique_by_area[0]
            return GeographyResult(
                match.canonical_area,
                match.scope,
                "matched",
                match.method,
                match.alias,
                match.priority,
                match.canonical_area,
                "|".join(sorted(set(quality_flags))),
                _join_sorted([match.alias]),
                match.method,
                str(match.priority),
            )

        candidates = sorted(unique_by_area, key=lambda match: (match.priority, match.canonical_area))
        if self._priority_resolves(candidates):
            match = candidates[0]
            return GeographyResult(
                match.canonical_area,
                match.scope,
                "matched",
                match.method,
                match.alias,
                match.priority,
                _join_sorted(match.canonical_area for match in candidates),
                "|".join(sorted(set(quality_flags + ["multiple_candidates_priority_resolved"]))),
                _join_sorted(match.alias for match in candidates),
                _join_sorted(match.method for match in candidates),
                _join_sorted(str(match.priority) for match in candidates),
            )

        return GeographyResult(
            pd.NA,
            "unknown",
            "ambiguous",
            "none",
            pd.NA,
            pd.NA,
            _join_sorted(match.canonical_area for match in candidates),
            "|".join(sorted(set(quality_flags + ["multiple_candidate_areas"]))),
            _join_sorted(match.alias for match in candidates),
            _join_sorted(match.method for match in candidates),
            _join_sorted(str(match.priority) for match in candidates),
        )

    def _candidate_matches(self, address_match_text: str) -> list[GeographyMatch]:
        """Return all alias candidates found with controlled matching rules."""

        components = {component.strip() for component in address_match_text.split(",") if component.strip()}
        matches: list[GeographyMatch] = []
        for alias in self.aliases:
            if alias.match_type == "exact_address":
                if alias.alias_match_text in components or alias.alias_match_text == address_match_text:
                    method = "exact_normalized_alias"
                else:
                    continue
            elif alias.phrase_pattern.search(address_match_text):
                method = alias.match_type
            else:
                continue
            matches.append(GeographyMatch(alias.canonical_area, alias.scope, method, alias.alias, alias.match_priority))
        return matches

    @staticmethod
    def _best_by_area(matches: list[GeographyMatch]) -> list[GeographyMatch]:
        """Keep the best alias candidate for each canonical area."""

        best: dict[str, GeographyMatch] = {}
        for match in matches:
            existing = best.get(match.canonical_area)
            if existing is None or (match.priority, match.alias) < (existing.priority, existing.alias):
                best[match.canonical_area] = match
        return list(best.values())

    @staticmethod
    def _priority_resolves(candidates: list[GeographyMatch]) -> bool:
        """Return whether explicit priority can defensibly resolve overlap."""

        if len(candidates) < 2:
            return True
        first, second = candidates[0], candidates[1]
        return first.priority <= 10 and second.priority >= 80 and _alias_contains(first.alias, second.alias)

    @staticmethod
    def _blocked_by_context(match: GeographyMatch, address_match_text: str) -> bool:
        """Block known broad-context false positives for a candidate."""

        if match.canonical_area == "Dún Laoghaire" and re.search(r"DUN\s+LAOGHAIRE\s*(?:-\s*)?RATHDOWN", address_match_text):
            return True
        return False

    @staticmethod
    def _from_override(match: GeographyMatch) -> GeographyResult:
        """Convert a valid manual override into final output fields."""

        return GeographyResult(
            match.canonical_area,
            match.scope,
            "manual_override",
            "manual_override",
            match.alias,
            match.priority,
            match.canonical_area,
            "manual_override_applied",
            match.alias,
            match.method,
            str(match.priority),
        )

    @staticmethod
    def _quality_flags(address_match_text: str, county_text: str, matches: list[GeographyMatch]) -> list[str]:
        """Build deterministic geography quality flags for one row."""

        flags: list[str] = []
        if POSTAL_DISTRICT_ONLY.match(address_match_text) or address_match_text in BROAD_DUBLIN_REFERENCES:
            flags.append("broad_dublin_reference_only")
        if matches and county_text and county_text != "DUBLIN":
            flags.append("conflicting_county_context")
        if any(match.canonical_area in NON_UNIQUE_AREAS for match in matches):
            flags.append("non_unique_locality_name")
        return flags


def enrich_with_geography(
    frame: pd.DataFrame,
    *,
    canonical_areas_path: str | Path,
    overrides_path: str | Path,
) -> pd.DataFrame:
    """Append address-normalisation and geography fields to a frame.

    Args:
        frame: Checkpoint 2 source-standardised frame.
        canonical_areas_path: CSV path for reviewed canonical aliases.
        overrides_path: CSV path for reviewed manual overrides.

    Returns:
        A copy of `frame` with Checkpoint 3 fields appended.
    """

    aliases = load_canonical_aliases(canonical_areas_path)
    overrides = load_manual_overrides(overrides_path, aliases)
    mapper = GeographyMapper(aliases, overrides)
    output = normalize_address_frame(frame)
    results = output.apply(mapper.map_record, axis=1)
    for field in GEOGRAPHY_FIELDS[4:]:
        output[field.name] = results.apply(lambda result, name=field.name: getattr(result, name))
    return output


def checkpoint3_arrow_schema(input_schema: pa.Schema) -> pa.Schema:
    """Build the physical Checkpoint 3 schema from the input schema.

    Args:
        input_schema: Checkpoint 2 PyArrow schema.

    Returns:
        Input fields followed by documented Checkpoint 3 fields.

    Raises:
        Checkpoint3PhysicalSchemaError: If any Checkpoint 3 field already
            exists in the input schema.
    """

    existing = {field.name for field in input_schema}
    duplicate = existing.intersection(field.name for field in GEOGRAPHY_FIELDS)
    if duplicate:
        raise Checkpoint3PhysicalSchemaError(f"Checkpoint 3 fields already exist in input schema: {sorted(duplicate)}")
    return pa.schema(list(input_schema) + GEOGRAPHY_FIELDS)


def dataframe_to_checkpoint3_table(frame: pd.DataFrame, input_schema: pa.Schema) -> pa.Table:
    """Convert an enriched frame to a PyArrow table with explicit schema.

    Args:
        frame: Enriched Checkpoint 3 frame.
        input_schema: Checkpoint 2 schema to preserve.

    Returns:
        PyArrow table ordered by the explicit Checkpoint 3 schema.

    Raises:
        Checkpoint3PhysicalSchemaError: If required output fields are missing.
    """

    schema = checkpoint3_arrow_schema(input_schema)
    missing = [field.name for field in schema if field.name not in frame.columns]
    if missing:
        raise Checkpoint3PhysicalSchemaError(f"Missing Checkpoint 3 output fields: {missing}")
    frame_for_arrow = frame[[field.name for field in schema]].copy()
    return pa.Table.from_pandas(frame_for_arrow, schema=schema, preserve_index=False)


def write_checkpoint3_parquet(frame: pd.DataFrame, input_schema: pa.Schema, path: str | Path) -> pa.Schema:
    """Write the geography-enriched Parquet output.

    Args:
        frame: Enriched Checkpoint 3 frame.
        input_schema: Checkpoint 2 schema to preserve.
        path: Destination Parquet path.

    Returns:
        Schema written to disk.
    """

    table = dataframe_to_checkpoint3_table(frame, input_schema)
    pq.write_table(table, path)
    return table.schema


def validate_checkpoint3_parquet(path: str | Path, input_schema: pa.Schema, expected_row_count: int) -> pa.Schema:
    """Read back and validate the Checkpoint 3 Parquet output.

    Args:
        path: Parquet path to validate.
        input_schema: Checkpoint 2 schema used to derive expected schema.
        expected_row_count: Required row count.

    Returns:
        Read-back PyArrow schema.

    Raises:
        Checkpoint3PhysicalSchemaError: If row count or physical schema differs
            from expectations.
    """

    table = pq.read_table(path)
    expected_schema = checkpoint3_arrow_schema(input_schema)
    if table.num_rows != expected_row_count:
        raise Checkpoint3PhysicalSchemaError(f"Expected {expected_row_count} rows, got {table.num_rows}")
    if table.schema.remove_metadata() != expected_schema.remove_metadata():
        raise Checkpoint3PhysicalSchemaError(
            "Checkpoint 3 physical schema validation failed.\n"
            f"Expected:\n{expected_schema}\n\nActual:\n{table.schema}"
        )
    return table.schema


def _phrase_pattern(alias_match_text: str) -> re.Pattern[str]:
    """Compile a token-boundary phrase pattern for an alias."""

    escaped = re.escape(alias_match_text).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Z0-9]){escaped}(?![A-Z0-9])")


def _has_dublin_context(address_match_text: str, county_text: str) -> bool:
    """Return whether row evidence places the address in Dublin context."""

    return county_text == "DUBLIN" or bool(re.search(r"(?<![A-Z0-9])(?:DUBLIN|CO DUBLIN|COUNTY DUBLIN)(?![A-Z0-9])", address_match_text))


def _maybe_dublin(address_match_text: str, county_text: str) -> bool:
    """Return whether Dublin context is present or not contradicted."""

    return _has_dublin_context(address_match_text, county_text) or not county_text


def _join_sorted(values: Any) -> str:
    """Join unique non-empty values in deterministic pipe-delimited order."""

    return "|".join(sorted({str(value) for value in values if str(value)}))


def _alias_contains(preferred_alias: str, other_alias: str) -> bool:
    """Return whether one normalised alias text contains another."""

    preferred = match_text(preferred_alias)
    other = match_text(other_alias)
    return preferred != other and other in preferred
