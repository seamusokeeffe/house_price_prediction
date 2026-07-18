"""Deterministic address normalisation for PPR Checkpoint 3.

This module preserves the raw address, creates an uppercase display
normalisation, and creates a separate accent-folded matching form.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import pandas as pd


TOO_SHORT_TOKEN_COUNT = 2

APOSTROPHE_TRANSLATION = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u00b4": "'",
    "`": "'",
})

DASH_TRANSLATION = str.maketrans({
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
})

SAFE_ABBREVIATIONS = {
    "RD": "ROAD",
    "ST": "STREET",
    "AVE": "AVENUE",
    "AV": "AVENUE",
    "CO": "COUNTY",
}


@dataclass(frozen=True)
class NormalizedAddress:
    """Normalised address fields emitted by Checkpoint 3.

    Attributes:
        raw_address: Original source value, preserved unchanged where present.
        address_normalized: Conservative uppercase normalised address.
        address_match_text: Accent-folded comparison text used for matching.
        address_normalization_status: One of `normalized`, `missing`, or
            `too_short`.
        address_quality_flags: Pipe-delimited deterministic quality flags.
    """

    raw_address: str | pd.NA
    address_normalized: str | pd.NA
    address_match_text: str | pd.NA
    address_normalization_status: str
    address_quality_flags: str


def normalize_address(value: Any) -> NormalizedAddress:
    """Normalise one raw address without dropping meaningful tokens.

    Args:
        value: Raw address-like value from the source dataset.

    Returns:
        A `NormalizedAddress` with raw, normalised, match-text, status, and
        quality-flag fields.
    """

    raw_value = pd.NA if pd.isna(value) else str(value)
    text = "" if pd.isna(raw_value) else str(raw_value)
    if text.strip() == "":
        return NormalizedAddress(raw_value, pd.NA, pd.NA, "missing", "missing_raw_address")

    normalized = _normalize_text(text)
    if not re.search(r"[A-Z0-9]", normalized):
        return NormalizedAddress(raw_value, pd.NA, pd.NA, "missing", "punctuation_only_address")

    flags = []
    tokens = re.findall(r"[A-Z0-9]+", normalized)
    if len(tokens) < TOO_SHORT_TOKEN_COUNT:
        flags.append("too_short_address")
        status = "too_short"
    else:
        status = "normalized"

    if _broad_locality_only(normalized):
        flags.append("broad_locality_only")

    return NormalizedAddress(
        raw_value,
        normalized,
        fold_accents(normalized),
        status,
        "|".join(flags),
    )


def normalize_address_frame(frame: pd.DataFrame, *, source_column: str = "raw_address") -> pd.DataFrame:
    """Append Checkpoint 3 address-normalisation fields to a frame.

    Args:
        frame: Input frame containing the raw address column.
        source_column: Column to normalise. Defaults to `raw_address`.

    Returns:
        A copy of `frame` with address-normalisation columns appended.
    """

    results = frame[source_column].apply(normalize_address)
    output = frame.copy()
    output["address_normalized"] = results.apply(lambda result: result.address_normalized)
    output["address_match_text"] = results.apply(lambda result: result.address_match_text)
    output["address_normalization_status"] = results.apply(lambda result: result.address_normalization_status)
    output["address_quality_flags"] = results.apply(lambda result: result.address_quality_flags)
    return output


def fold_accents(value: str) -> str:
    """Return `value` with Unicode combining accents removed.

    Args:
        value: Text to fold.

    Returns:
        Accent-folded text.
    """

    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def match_text(value: Any) -> str:
    """Build deterministic comparison text for aliases and addresses.

    Args:
        value: Raw text-like value.

    Returns:
        Uppercase normalised and accent-folded text, or an empty string for
        missing values.
    """

    if pd.isna(value):
        return ""
    return fold_accents(_normalize_text(str(value)))


def _normalize_text(value: str) -> str:
    """Apply conservative punctuation, spacing, case, and abbreviation rules."""

    text = unicodedata.normalize("NFC", value)
    text = text.translate(APOSTROPHE_TRANSLATION).translate(DASH_TRANSLATION)
    text = text.upper().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r",\s*,+", ", ", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\b([A-Z]{1,4})\.(?=\s|,|$)", r"\1", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+,", ",", text)
    text = text.strip(" ,.")
    text = _expand_safe_abbreviations(text)
    return text


def _expand_safe_abbreviations(value: str) -> str:
    """Expand only reviewed abbreviations with low ambiguity."""

    def replace(match: re.Match[str]) -> str:
        return SAFE_ABBREVIATIONS.get(match.group(0), match.group(0))

    return re.sub(r"\b(?:RD|ST|AVE|AV|CO)\b", replace, value)


def _broad_locality_only(value: str) -> bool:
    """Return whether text appears to contain locality but no address detail."""

    tokens = re.findall(r"[A-Z0-9]+", fold_accents(value))
    if not tokens:
        return False
    broad_terms = {"DUBLIN", "COUNTY", "CO", "IRELAND"}
    locality_without_detail = len(tokens) <= 3 and not any(token.isdigit() for token in tokens)
    return locality_without_detail and not set(tokens).issubset(broad_terms)
